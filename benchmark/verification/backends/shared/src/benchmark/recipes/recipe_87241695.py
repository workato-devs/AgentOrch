from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_87241695


RECIPE_ID = "87241695"
SEED_TYPE = "sheets_pto_repeat_block_dm_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "aed2f0c4"
SEARCH_AS = "329ab153"
FOREACH_AS = "fecbd8a2"
POST_AS = "582c85b9"


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "aed2f0c4", "skip": false, "input": {"days_of_week": "1", "time_unit": "weeks", "trigger_at": "00:00:00", "trigger_every": "1"}, "block": [{"number": 2, "keyword": "action", "provider": "google_sheets", "name": "search_spreadsheet_rows_v4_new", "as": "329ab153", "skip": false, "input": {"count": "200", "data": {"col_Future": "Yes"}, "sheet": "PTO BOT", "spreadsheet": "1oPfX-9j2ZL4IEyMAfJ3vwzEUywXG8LqrO5YD6twpzac", "team_drives": "my_drive"}, "block": []}, {"number": 3, "keyword": "foreach", "provider": "", "name": "", "as": "fecbd8a2", "skip": false, "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"329ab153\",\"path\":[\"rows\"]}')}"}, "repeat_mode": "simple", "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"329ab153\",\"path\":[\"rows\"]}')}", "block": [{"number": 4, "keyword": "action", "provider": "slack_bot", "name": "post_bot_message", "as": "582c85b9", "skip": false, "input": {"blocks": [{"block_type": "repeat_block_group", "button_type": "continue_flow", "objects": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"329ab153\",\"path\":[\"rows\"]}')}", "blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": "The following are the PTO for the week:\n\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"fecbd8a2\",\"path\":[\"col_Requested_By\"]}')}: #{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"fecbd8a2\",\"path\":[\"col_Start_Date\"]}')}-#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"fecbd8a2\",\"path\":[\"col_End_Date\"]}')}"}]}}], "channel": "U02T2EDQD1U"}, "block": []}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SEARCH_AS, "google_sheets", "search_spreadsheet_rows_v4_new"),
    (POST_AS, "slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "google_sheets.search_spreadsheet_rows_v4_new",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
_SEARCH_INPUT = _EXPECTED_TREE["block"][0]["input"]
_POST_NODE = _EXPECTED_TREE["block"][1]["block"][0]
CHANNEL_LITERAL = str(_POST_NODE["input"]["channel"])
SEARCH_CRITERIA = dict(_SEARCH_INPUT["data"])
SEARCH_COUNT = str(_SEARCH_INPUT["count"])
SPREADSHEET_LITERAL = str(_SEARCH_INPUT["spreadsheet"])
SHEET_LITERAL = str(_SEARCH_INPUT["sheet"])
MATCH_HEADER = "Future"
MATCH_VALUE = str(SEARCH_CRITERIA["col_Future"])
LINE_PREFIX = "The following are the PTO for the week:\n\n"
SHEET_HEADERS = ("Email", "Requested_By", "Start_Date", "End_Date", "Future")
PILL_HEADERS = ("Requested_By", "Start_Date", "End_Date")
REQUIRED_EXPECT_KEYS = (
    "case",
    "search_row_count",
    "message_lines",
    "repeat_count",
    "slack_texts",
    "executed_action_count",
    "tools",
    "tool_expectations",
)
_EXPECTATION_TARGET_KEYS = {"tool", "channel"}
_EXPECTATION_VALUE_KEYS = {"args_contains", "result_count", "text_fragments"}


def validate_87241695(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Named traps on top of the byte pin.
    blocks = _POST_NODE["input"].get("blocks")
    if (
        not isinstance(blocks, list)
        or len(blocks) != 1
        or blocks[0].get("block_type") != "repeat_block_group"
        or "____source" not in (blocks[0].get("objects") or {})
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the single repeat_block_group with objects.____source "
            "changed -- the repetition analysis no longer holds"
        )
    inner = (blocks[0].get("objects") or {}).get("blocks")
    if (
        not isinstance(inner, list)
        or len(inner) != 1
        or inner[0].get("block_type") != "section_with_text"
        or not str(inner[0].get("section_text") or "").startswith(LINE_PREFIX)
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} inner section_with_text changed")
    if CHANNEL_LITERAL != "U02T2EDQD1U":
        raise RuntimeError(
            f"recipe {RECIPE_ID} channel literal changed: {CHANNEL_LITERAL!r} -- re-check "
            "the slack_channel_map requirement before building"
        )
    foreachs = [node for node in _walk_nodes(raw) if node.get("keyword") == "foreach"]
    if (
        len(foreachs) != 1
        or str(foreachs[0].get("as") or "") != FOREACH_AS
        or foreachs[0].get("repeat_mode") != "simple"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} foreach step changed")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    for keyword in ("if", "elsif", "else", "stop", "repeat", "try", "catch"):
        if any(node.get("keyword") == keyword for node in _walk_nodes(raw)):
            raise RuntimeError(f"recipe {RECIPE_ID} unexpectedly contains a {keyword} block")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "channel_literal": CHANNEL_LITERAL,
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


def seed_87241695(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_87241695(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less scheduler "
            f"tick; no trigger field is ever dereferenced): {trigger!r}"
        )
    for key in ("force_action_error", "job_context", "now"):
        if data.get(key) is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} has no catch/clock-pill/time formula: variant key "
                f"{key!r} must not be declared"
            )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in) != ["sheets", "slack_channel_map"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the sheets and "
            f"slack_channel_map sections: "
            f"{sorted(seed_in) if isinstance(seed_in, dict) else seed_in!r}"
        )
    if seed_in["slack_channel_map"] != {CHANNEL_LITERAL: "__override__"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.slack_channel_map must map the literal DM user id "
            f"to the override channel exactly ({{{CHANNEL_LITERAL!r}: '__override__'}}); "
            "posting to the raw U-id would DM a real user: "
            f"{seed_in['slack_channel_map']!r}"
        )
    sheet_rows = _require_sheets_section(seed_in["sheets"])
    derived = _derive_ground_truth(sheet_rows)
    _require_expect_shape(data.get("expect"), derived)
    seed_response = ctx.tools.call(
        "harness.google_sheets.seed_rows", {"sheets": seed_in["sheets"]}
    )
    if not seed_response.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Google Sheets seed failed: {seed_response}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "sheets": deepcopy(seed_in["sheets"]),
        "sheets_seed_response": deepcopy(seed_response),
        "slack_channel_map": deepcopy(seed_in["slack_channel_map"]),
        "expect": deepcopy(data["expect"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_87241695(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_87241695(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("sheets"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing sheets section")
    if seed.get("slack_channel_map") != {CHANNEL_LITERAL: "__override__"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed file must carry the exact slack_channel_map "
            "override routing"
        )
    if seed.get("trigger") != {}:
        raise RuntimeError(f"recipe {RECIPE_ID} seed trigger must be the explicit payload-less {{}}")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    # Read-only recipe over a fully re-seeded tab + terminal Slack posts:
    # no cleanup step exists by design (cleanup principle -- the seed
    # overwrites all sheet state per run; posts are never re-read).
    initial_snapshot = ctx.tools.call("harness.google_sheets.snapshot", {})
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = ctx.tools.call("harness.google_sheets.snapshot", {})
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
            "sheets_seed": deepcopy(seed.get("sheets")),
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_87241695(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_sheets_section(section: Any) -> list[dict[str, str]]:
    if not isinstance(section, dict) or sorted(section) != ["headers", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets must be exactly {{'headers', 'rows'}}"
        )
    if list(section["headers"]) != list(SHEET_HEADERS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} bench tab headers must be exactly {list(SHEET_HEADERS)} "
            "(underscored schema forms -- the pill alias map is byte-exact alias[4:], so "
            f"space-form headers break every pill deref): {section['headers']!r}"
        )
    rows = section["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.sheets.rows must be a list")
    if len(rows) >= int(SEARCH_COUNT):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed rows must stay below the connector count "
            f"{SEARCH_COUNT} (the cap must never bind -- a capped result would silently "
            f"change the repeat multiplier)"
        )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row) != sorted(SHEET_HEADERS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} sheet row {idx} must fill exactly the pinned headers: "
                f"{row!r}"
            )
        for header, value in row.items():
            if not isinstance(value, str) or value == "":
                raise RuntimeError(
                    f"recipe {RECIPE_ID} sheet row {idx}.{header} must be a non-empty "
                    f"string (Sheets reads empty cells back as '' -- seed the intent "
                    f"explicitly): {value!r}"
                )
    return [dict(row) for row in rows]


def _derive_ground_truth(sheet_rows: list[dict[str, str]]) -> dict[str, Any]:
    matching = [row for row in sheet_rows if row[MATCH_HEADER] == MATCH_VALUE]
    lines = [
        LINE_PREFIX
        + f"{row['Requested_By']}: {row['Start_Date']}-{row['End_Date']}"
        for row in matching
    ]
    repeat = len(matching)
    texts = ["\n".join([line] * repeat) for line in lines]
    return {
        "search_row_count": repeat,
        "message_lines": lines,
        "repeat_count": repeat,
        "slack_texts": texts,
    }


def _require_expect_shape(expect: Any, derived: dict[str, Any]) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if not isinstance(expect.get("case"), str) or not expect["case"].strip():
        raise RuntimeError(f"recipe {RECIPE_ID} expect.case must describe the variant branch")
    count = derived["search_row_count"]
    checks = (
        expect.get("search_row_count") == count,
        expect.get("message_lines") == derived["message_lines"],
        expect.get("repeat_count") == derived["repeat_count"],
        expect.get("slack_texts") == derived["slack_texts"],
        expect.get("executed_action_count") == 1 + count,
        expect.get("tools")
        == ["google_sheets.search_spreadsheet_rows_v4_new"] + ["slack.post_message"] * count,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with the derived ground "
            f"truth {derived!r}: {expect!r}"
        )
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or len(items) != 1 + count or not all(
        isinstance(item, dict) for item in items
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin the search call and "
            f"every one of the {count} slack posts"
        )
    for idx, item in enumerate(items):
        unknown = sorted(set(item) - _EXPECTATION_TARGET_KEYS - _EXPECTATION_VALUE_KEYS)
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] has non-corpus keys: {unknown}"
            )
    search_item = items[0]
    if (
        search_item.get("tool") != "google_sheets.search_spreadsheet_rows_v4_new"
        or search_item.get("args_contains")
        != {
            "spreadsheet": SPREADSHEET_LITERAL,
            "sheet": SHEET_LITERAL,
            "data": SEARCH_CRITERIA,
            "count": SEARCH_COUNT,
        }
        or search_item.get("result_count") != count
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] must pin the verbatim search args "
            f"and result_count {count}: {search_item!r}"
        )
    for offset, text in enumerate(derived["slack_texts"]):
        item = items[1 + offset]
        if (
            item.get("tool") != "slack.post_message"
            or item.get("channel") != "override"
            or item.get("args_contains") != {"text": text}
            or item.get("text_fragments") != [derived["message_lines"][offset]]
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{1 + offset}] must pin the full "
                f"repeated text, its line fragment and the override-channel routing: "
                f"{item!r}"
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


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
