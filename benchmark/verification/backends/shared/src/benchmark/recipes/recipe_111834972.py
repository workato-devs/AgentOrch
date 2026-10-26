from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_111834972


RECIPE_ID = "111834972"
SEED_TYPE = "exec_connects_dupe_connection_rollup_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "edb926d8"
DECLARE_AS = "c9233398"
SEARCH_AS = "2cf1ef12"
LOGGER_AS = "f78d1fc6"
FOREACH_AS = "80b3e785"
UPDATE_VAR_AS = "ae4bdbd4"
LOOP_UPDATE_AS = "c5c84e5b"
SEARCH2_AS = "9cd61e14"
FINAL_UPDATE_AS = "ef42b08e"
RETURN_AS = "c6c7d67d"
ANON_LINE = "<anon>b1a2c3d4</anon>"
ANON_TARGET = "<anon>aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee</anon>:<anon>b1a2c3d4</anon>:connection_cell"
SHEET_HEADERS = [
    "First Name",
    "Last Name",
    "URL",
    "Email Address",
    "Company",
    "Position",
    "Connection",
    "Dupe?",
    "Recipe Note",
]


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "workato_recipe_function", "name": "execute", "as": "edb926d8", "skip": false, "input": {"parameters_schema_json": "[{\"name\":\"URL\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"URL\"},{\"name\":\"Row\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Row\"}]", "result_schema_json": "[]"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "c9233398", "skip": false, "input": {"variables": {"schema": "[{\"name\":\"connection_cell\",\"type\":\"string\",\"optional\":true,\"label\":\"Connection Cell\",\"details\":{\"real_name\":\"Connection Cell\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"}}, "block": []}, {"number": 3, "keyword": "action", "provider": "google_sheets", "name": "search_spreadsheet_rows_v4_new", "as": "2cf1ef12", "skip": false, "input": {"count": "200", "data": {"col_URL": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"edb926d8\",\"path\":[\"parameters\", \"URL\"]}')}"}, "sheet": "Sheet2", "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>", "team_drives": "my_drive"}, "block": []}, {"number": 4, "keyword": "action", "provider": "logger", "name": "log_message", "as": "f78d1fc6", "skip": false, "input": {"message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"2cf1ef12\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}", "user_logs_enabled": "false"}, "block": []}, {"number": 5, "keyword": "foreach", "provider": "", "name": "", "as": "80b3e785", "skip": false, "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"2cf1ef12\",\"path\":[\"rows\"]}')}"}, "repeat_mode": "simple", "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"2cf1ef12\",\"path\":[\"rows\"]}')}", "block": [{"number": 6, "keyword": "action", "provider": "workato_variable", "name": "update_variables", "as": "ae4bdbd4", "skip": false, "input": {"connection_cell": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"<anon>b1a2c3d4</anon>\",\"path\":[\"connection_cell\"]}')}\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"80b3e785\",\"path\":[\"col_Connection\"]}')}", "name": "<anon>aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee</anon>:<anon>b1a2c3d4</anon>:connection_cell"}, "block": []}, {"number": 7, "keyword": "action", "provider": "google_sheets", "name": "update_row_v4_new", "as": "c5c84e5b", "skip": false, "input": {"data": {"col_Recipe Note": "#{_dp('{\"pill_type\":\"foreach_meta\",\"provider\":\"foreach\",\"line\":\"80b3e785\",\"key\":\"index\"}')}"}, "row_number": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"80b3e785\",\"path\":[\"row_number\"]}')}", "sheet": "Sheet2", "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>", "team_drives": "my_drive"}, "block": []}]}, {"number": 8, "keyword": "action", "provider": "google_sheets", "name": "search_spreadsheet_rows_v4_new", "as": "9cd61e14", "skip": false, "input": {"count": "200", "data": {"col_Recipe Note": "0", "col_URL": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"edb926d8\",\"path\":[\"parameters\", \"URL\"]}')}"}, "sheet": "Sheet2", "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>", "team_drives": "my_drive"}, "block": []}, {"number": 9, "keyword": "action", "provider": "google_sheets", "name": "update_row_v4_new", "as": "ef42b08e", "skip": false, "input": {"data": {"col_Connection": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"<anon>b1a2c3d4</anon>\",\"path\":[\"connection_cell\"]}')}", "col_Recipe Note": "KEEP"}, "row_number": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9cd61e14\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"row_number\"]}')}", "sheet": "Sheet2", "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>", "team_drives": "my_drive"}, "block": []}, {"number": 10, "keyword": "action", "provider": "workato_recipe_function", "name": "return_result", "as": "c6c7d67d", "skip": false, "input": {}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (DECLARE_AS, "workato_variable", "declare_variable"),
    (SEARCH_AS, "google_sheets", "search_spreadsheet_rows_v4_new"),
    (LOGGER_AS, "logger", "log_message"),
    (UPDATE_VAR_AS, "workato_variable", "update_variables"),
    (LOOP_UPDATE_AS, "google_sheets", "update_row_v4_new"),
    (SEARCH2_AS, "google_sheets", "search_spreadsheet_rows_v4_new"),
    (FINAL_UPDATE_AS, "google_sheets", "update_row_v4_new"),
    (RETURN_AS, "workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "google_sheets.search_spreadsheet_rows_v4_new",
    "workato_runtime.log_message",
    "workato_runtime.update_variables",
    "google_sheets.update_row_v4_new",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "google_sheets.search_spreadsheet_rows_v4_new",
    "google_sheets.update_row_v4_new",
    "workato_recipe_function.return_result",
]
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "matched_row_count",
    "logger_message",
    "connection_cell_updates",
    "loop_note_writes",
    "final_connection_value",
    "return_value",
    "initial_sheet_rows",
    "final_sheet_rows",
)


def validate_111834972(raw: dict[str, Any]) -> dict[str, Any]:
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
    nodes = {str(node.get("as") or ""): node for node in _walk_nodes(raw)}
    # Semantic pins (the tree pin holds the bytes; these name the traps):
    # 1. the declare stays SCHEMA-ONLY (nil variable; its result is {} and the
    #    anon-tagged writes must never resolve to it),
    declare_vars = (nodes[DECLARE_AS].get("input") or {}).get("variables") or {}
    if "data" in declare_vars:
        raise RuntimeError(
            f"recipe {RECIPE_ID} declare gained a data default; the nil-declare/anon-store "
            f"semantics would change: {declare_vars!r}"
        )
    # 2. the update target keeps the VERBATIM anonymizer-tagged name and the
    #    accumulation template reads the SAME tagged line,
    update_input = nodes[UPDATE_VAR_AS].get("input") or {}
    if str(update_input.get("name")) != ANON_TARGET:
        raise RuntimeError(
            f"recipe {RECIPE_ID} update_variables target changed (do NOT 'fix' the anon "
            f"tags -- they are self-consistent): {update_input.get('name')!r}"
        )
    value_template = str(update_input.get("connection_cell") or "")
    if ANON_LINE not in value_template or f'"line":"{FOREACH_AS}"' not in value_template:
        raise RuntimeError(
            f"recipe {RECIPE_ID} accumulation template changed: {value_template!r}"
        )
    # 3. the loop write targets col_Recipe Note with the foreach_meta index,
    loop_data = (nodes[LOOP_UPDATE_AS].get("input") or {}).get("data") or {}
    if sorted(loop_data.keys()) != ["col_Recipe Note"] or "foreach_meta" not in str(
        loop_data.get("col_Recipe Note")
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} loop note write changed: {loop_data!r}")
    # 4. the step-8 search keys on BOTH the literal '0' note and the URL,
    search2_data = (nodes[SEARCH2_AS].get("input") or {}).get("data") or {}
    if str(search2_data.get("col_Recipe Note")) != "0" or "col_URL" not in search2_data:
        raise RuntimeError(f"recipe {RECIPE_ID} step-8 search filters changed: {search2_data!r}")
    # 5. the final write carries the accumulated variable + the literal KEEP.
    final_data = (nodes[FINAL_UPDATE_AS].get("input") or {}).get("data") or {}
    if (
        str(final_data.get("col_Recipe Note")) != "KEEP"
        or ANON_LINE not in str(final_data.get("col_Connection"))
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} final write changed: {final_data!r}")
    foreach = nodes.get(FOREACH_AS) or next(
        (node for node in _walk_nodes(raw) if node.get("keyword") == "foreach"), {}
    )
    if str(foreach.get("repeat_mode")) != "simple" or SEARCH_AS not in str(foreach.get("source")):
        raise RuntimeError(f"recipe {RECIPE_ID} foreach changed: {foreach.get('source')!r}")
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


def seed_111834972(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_111834972(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no try/catch: a forced action error would fail the whole "
            "run instead of exercising a recipe branch"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["google_sheets"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the google_sheets section; got "
            f"{sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    sheets_section = _require_sheets_section(
        seed_in["google_sheets"], str(trigger["parameters"]["URL"])
    )
    expect = data.get("expect")
    _require_expect_shape(expect)
    provision = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": sheets_section})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Google Sheets seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "google_sheets": deepcopy(sheets_section),
        "sheets_seed_response": deepcopy(provision),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_111834972(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_111834972(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("google_sheets"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing google_sheets section")
    _require_trigger_shape(seed.get("trigger") or {})
    if not ctx.env.sheets_spreadsheet_id or not ctx.env.sheets_tab:
        raise RuntimeError("missing SHEETS_SPREADSHEET_ID or SHEETS_TAB for live Google Sheets")
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
            "expect": seed.get("expect"),
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_111834972(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["parameters"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'parameters': ...}}; "
            f"got {sorted(trigger.keys())}"
        )
    parameters = trigger["parameters"]
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters must be an object")
    unknown = sorted(set(parameters.keys()) - {"URL", "Row"})
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters has unknown keys: {unknown}")
    url = parameters.get("URL")
    if not isinstance(url, str) or not url.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} parameters.URL must be a non-empty string (both searches "
            f"filter on it): {url!r}"
        )
    if "Row" in parameters and not isinstance(parameters["Row"], str):
        raise RuntimeError(
            f"recipe {RECIPE_ID} parameters.Row must be a string when present (declared but "
            f"unused by every step): {parameters['Row']!r}"
        )


def _require_sheets_section(section: Any, url: str) -> dict[str, Any]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["headers", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.google_sheets must be exactly {{'headers','rows'}}"
        )
    if section.get("headers") != SHEET_HEADERS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.google_sheets.headers must be exactly the 9 ACTUAL "
            "(label) headers in schema order -- the engine aliases search rows with the "
            "col_ pill names while writes label-decode into these real columns"
        )
    rows = section.get("rows")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.google_sheets.rows must be a non-empty list")
    matches = 0
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(SHEET_HEADERS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} sheet row {idx} must carry exactly the 9 headers; got "
                f"{sorted(row.keys()) if isinstance(row, dict) else row!r}"
            )
        for key, value in row.items():
            if not isinstance(value, str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} sheet row {idx} {key!r} must be a string "
                    "(rendered-form pinning)"
                )
            if "\n" in value:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} sheet row {idx} {key!r} must be single-line "
                    "(only the recipe's own final write produces the multi-line cell)"
                )
        if row["URL"] == url:
            matches += 1
    if matches < 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} needs at least one row whose URL equals the trigger URL: "
            "with zero matches the foreach runs 0 iterations and the step-9 row_number pill "
            "resolves MISSING -> the live update_row faithfully errors the job (the recipe's "
            "unguarded edge, a job error rather than a representable branch)"
        )
    return {"headers": list(SHEET_HEADERS), "rows": deepcopy(rows)}


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    matched = expect.get("matched_row_count")
    if not isinstance(matched, int) or matched < 1:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.matched_row_count must be >= 1")
    # 3 fixed actions + 2 per iteration + search2 + final update + return.
    if expect.get("executed_action_count") != 3 + 2 * matched + 3:
        raise RuntimeError(
            f"recipe {RECIPE_ID} executed_action_count must be 6 + 2*matches "
            f"({6 + 2 * matched}): {expect.get('executed_action_count')!r}"
        )
    expected_tools = (
        ["google_sheets.search_spreadsheet_rows_v4_new"]
        + ["google_sheets.update_row_v4_new"] * matched
        + [
            "google_sheets.search_spreadsheet_rows_v4_new",
            "google_sheets.update_row_v4_new",
            "workato_recipe_function.return_result",
        ]
    )
    if expect.get("tools") != expected_tools:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools must be the search/loop-writes/search/write/"
            f"return sequence for {matched} matches: {expect.get('tools')!r}"
        )
    updates = expect.get("connection_cell_updates")
    if (
        not isinstance(updates, list)
        or len(updates) != matched
        or not all(isinstance(item, str) and item.startswith("\n") for item in updates)
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.connection_cell_updates must pin one accumulated "
            f"string per iteration, each with the faithful LEADING newline (nil first read): "
            f"{updates!r}"
        )
    if expect.get("final_connection_value") != (updates[-1] if updates else None):
        raise RuntimeError(
            f"recipe {RECIPE_ID} final_connection_value must equal the last accumulation"
        )
    notes = expect.get("loop_note_writes")
    if (
        not isinstance(notes, list)
        or len(notes) != matched
        or [note[1] for note in notes if isinstance(note, list) and len(note) == 2]
        != list(range(matched))
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} loop_note_writes must pin [row_number, index] pairs with "
            f"0-based indexes in loop order: {notes!r}"
        )
    if expect.get("logger_message") != str(matched):
        raise RuntimeError(
            f"recipe {RECIPE_ID} logger_message must be the stringified match count: "
            f"{expect.get('logger_message')!r}"
        )
    if expect.get("return_value") != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} return_result is empty; expect.return_value must be {{}}"
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
    return {"google_sheets": ctx.tools.call("harness.google_sheets.snapshot", {})}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
