from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_121951507


RECIPE_ID = "121951507"
SEED_TYPE = "slack_app_home_team_gate_variant"
TRACK = "live_slack_app_home_publish"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "new_event"
TRIGGER_AS = "9b17fb0c"
GET_USER_AS = "ff6ae1d3"
SEARCH_AS = "2a70f21a"
ADMIN_HOME_AS = "2c4d9486"
DEFAULT_HOME_AS = "271782f8"
DEAD_TOP_AS = "49391591"    # skip:true editor leftover before the user lookup
DEAD_ELSE_AS = "98084ab8"  # skip:true inside the ELSE branch (twin has no such step)
DEAD_STEP_AS = (DEAD_TOP_AS, DEAD_ELSE_AS)
TABLE_ID = "3770006"
LIVE_MEMBER_ID = "U0B91BSRGF8"
LIVE_MEMBER_EMAIL = "jamie.lee@corp.example"
EMAIL_COL = "col3"
ROW_FIELDS = tuple(f"col{i}" for i in range(1, 11))



_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "slack_bot", "name": "new_event", "as": "9b17fb0c", "skip": false, "input": {"event_name": "app_home_opened"}, "block": [{"number": 2, "keyword": "action", "provider": "slack_bot", "name": "open_bot_app_home", "as": "49391591", "skip": true, "block": []}, {"number": 3, "keyword": "action", "provider": "slack_bot", "name": "get_user_by_email", "as": "ff6ae1d3", "skip": false, "input": {"id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"9b17fb0c\",\"path\":[\"app_home_opened\", \"user\"]}')}"}, "block": []}, {"number": 4, "keyword": "action", "provider": "lookup_table", "name": "search_entries", "as": "2a70f21a", "skip": false, "input": {"lookup_table_id": "3770006", "parameters": {"col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"ff6ae1d3\",\"path\":[\"profile\", \"email\"]}')}"}}, "block": []}, {"number": 5, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"2a70f21a\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}", "operand": "greater_than", "rhs": "0"}], "operand": "and", "type": "compound"}, "block": [{"number": 6, "keyword": "action", "provider": "slack_bot", "name": "open_bot_app_home", "as": "2c4d9486", "skip": false, "input": {"blocks": [{"alt_text": "Security Bot", "block_type": "image", "image_title": "SECURITY BOT", "image_url": "https://i.pinimg.com/736x/f1/82/79/f1827973d062e602527b4aed79c4ed39.jpg"}, {"block_type": "divider"}, {"block_type": "divider"}, {"block_type": "section_with_text", "section_text": "Welcome to the Security Bot!! I am here for any CyberSecurity related help. At your Service :alert-5:"}, {"block_type": "divider"}, {"block_type": "divider"}, {"block_type": "section_with_button", "bot_command": "52864867", "button_title": "Switch Profiles", "section_text": "Zscaler Switch Profiles :zscaler:", "style": "primary"}, {"block_type": "divider"}, {"block_type": "section_with_text", "section_text": "RPA Automation Documentation for reference - https://workato.atlassian.net/wiki/x/2oCrM"}, {"block_type": "divider"}, {"block_type": "divider"}, {"block_type": "section_with_button", "bot_command": "57790027", "button_title": "Grant USB Access", "section_text": "Grant USB Exception in Sentinel One :sentinelonelogo:", "style": "primary"}, {"block_type": "divider"}, {"block_type": "section_with_text", "section_text": "USB Exception Documentation for Reference - https://workato.atlassian.net/wiki/x/CYCVOQ"}, {"block_type": "divider"}, {"block_type": "section_with_button", "bot_command": "62930346", "button_title": "Report Incident", "section_text": "Report a Security Incident", "style": "danger"}], "user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"9b17fb0c\",\"path\":[\"app_home_opened\", \"user\"]}')}"}, "block": []}, {"number": 7, "keyword": "else", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 8, "keyword": "action", "provider": "slack_bot", "name": "open_bot_app_home", "as": "271782f8", "skip": false, "input": {"blocks": [{"alt_text": "Security Bot", "block_type": "image", "image_title": "SECURITY BOT", "image_url": "https://i.pinimg.com/736x/f1/82/79/f1827973d062e602527b4aed79c4ed39.jpg"}, {"block_type": "divider"}, {"block_type": "divider"}, {"block_type": "section_with_text", "section_text": "Welcome to the Security Bot!! I am here for any CyberSecurity related help. At your Service :alert-5:"}, {"block_type": "divider"}, {"block_type": "divider"}, {"block_type": "section_with_button", "bot_command": "59898460", "button_title": "Request USB Access", "section_text": "Request USB Exception :sentinelonelogo:", "style": "primary"}, {"block_type": "divider"}, {"attachment_fields": [{"title": "Confluence Link", "value": "\"https://workato.atlassian.net/wiki/x/7QAFQg\""}], "block_type": "section_with_fields", "section_text": "Please find below the Confluence page to get Serial ID of USB Device"}, {"block_type": "divider"}, {"block_type": "section_with_button", "bot_command": "62930346", "button_title": "Report Incident", "section_text": "Report a Security Incident", "style": "danger"}], "user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"9b17fb0c\",\"path\":[\"app_home_opened\", \"user\"]}')}"}, "block": []}, {"number": 9, "keyword": "action", "provider": "slack_bot", "name": "open_bot_app_home", "as": "98084ab8", "skip": true, "block": []}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

ADMIN_BLOCKS: list[dict[str, Any]] = json.loads(r"""[{"alt_text": "Security Bot", "block_type": "image", "image_title": "SECURITY BOT", "image_url": "https://i.pinimg.com/736x/f1/82/79/f1827973d062e602527b4aed79c4ed39.jpg"}, {"block_type": "divider"}, {"block_type": "divider"}, {"block_type": "section_with_text", "section_text": "Welcome to the Security Bot!! I am here for any CyberSecurity related help. At your Service :alert-5:"}, {"block_type": "divider"}, {"block_type": "divider"}, {"block_type": "section_with_button", "bot_command": "52864867", "button_title": "Switch Profiles", "section_text": "Zscaler Switch Profiles :zscaler:", "style": "primary"}, {"block_type": "divider"}, {"block_type": "section_with_text", "section_text": "RPA Automation Documentation for reference - https://workato.atlassian.net/wiki/x/2oCrM"}, {"block_type": "divider"}, {"block_type": "divider"}, {"block_type": "section_with_button", "bot_command": "57790027", "button_title": "Grant USB Access", "section_text": "Grant USB Exception in Sentinel One :sentinelonelogo:", "style": "primary"}, {"block_type": "divider"}, {"block_type": "section_with_text", "section_text": "USB Exception Documentation for Reference - https://workato.atlassian.net/wiki/x/CYCVOQ"}, {"block_type": "divider"}, {"block_type": "section_with_button", "bot_command": "62930346", "button_title": "Report Incident", "section_text": "Report a Security Incident", "style": "danger"}]""")
DEFAULT_BLOCKS: list[dict[str, Any]] = json.loads(r"""[{"alt_text": "Security Bot", "block_type": "image", "image_title": "SECURITY BOT", "image_url": "https://i.pinimg.com/736x/f1/82/79/f1827973d062e602527b4aed79c4ed39.jpg"}, {"block_type": "divider"}, {"block_type": "divider"}, {"block_type": "section_with_text", "section_text": "Welcome to the Security Bot!! I am here for any CyberSecurity related help. At your Service :alert-5:"}, {"block_type": "divider"}, {"block_type": "divider"}, {"block_type": "section_with_button", "bot_command": "59898460", "button_title": "Request USB Access", "section_text": "Request USB Exception :sentinelonelogo:", "style": "primary"}, {"block_type": "divider"}, {"attachment_fields": [{"title": "Confluence Link", "value": "\"https://workato.atlassian.net/wiki/x/7QAFQg\""}], "block_type": "section_with_fields", "section_text": "Please find below the Confluence page to get Serial ID of USB Device"}, {"block_type": "divider"}, {"block_type": "section_with_button", "bot_command": "62930346", "button_title": "Report Incident", "section_text": "Report a Security Incident", "style": "danger"}]""")

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (GET_USER_AS, "slack_bot", "get_user_by_email"),
    (SEARCH_AS, "lookup_table", "search_entries"),
    (ADMIN_HOME_AS, "slack_bot", "open_bot_app_home"),
    (DEFAULT_HOME_AS, "slack_bot", "open_bot_app_home"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "slack_bot.get_user_by_email",
    "lookup_table.search_entries",
    "slack_bot.open_bot_app_home",
]
ALLOWED_TOOLS: list[str] = [
    "slack_bot.get_user_by_email",
    "lookup_table.search_entries",
    "slack_bot.open_bot_app_home",
]
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "outcome",
    "member_email",
    "matched_entry_count",
    "home_step",
    "home_blocks",
)
OUTCOMES = ("admin_home", "default_home")
_USER_RE = re.compile(r"^U[A-Z0-9]{5,12}$")


def validate_121951507(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if str((raw.get("input") or {}).get("event_name") or "") != "app_home_opened":
        raise RuntimeError(f"recipe {RECIPE_ID} trigger event changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Semantic pins on the drift-prone bits (twin deltas live exactly here).
    search = next((n for n in _walk_nodes(raw) if str(n.get("as") or "") == SEARCH_AS), None)
    if not isinstance(search, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} search step {SEARCH_AS} missing")
    search_input = search.get("input") or {}
    if str(search_input.get("lookup_table_id") or "") != TABLE_ID:
        raise RuntimeError(
            f"recipe {RECIPE_ID} lookup table changed: "
            f"{search_input.get('lookup_table_id')!r} != {TABLE_ID!r} (twin drift?)"
        )
    search_params = search_input.get("parameters") or {}
    email_pill = str(search_params.get(EMAIL_COL) or "")
    if (
        sorted(search_params.keys()) != [EMAIL_COL]
        or GET_USER_AS not in email_pill
        or '"profile"' not in email_pill
        or '"email"' not in email_pill
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} search no longer keys col3 on ff6ae1d3 profile.email: "
            f"{search_params!r}"
        )
    for step_as, blocks in ((ADMIN_HOME_AS, ADMIN_BLOCKS), (DEFAULT_HOME_AS, DEFAULT_BLOCKS)):
        node = next((n for n in _walk_nodes(raw) if str(n.get("as") or "") == step_as), None)
        if not isinstance(node, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} app-home step {step_as} missing")
        if (node.get("input") or {}).get("blocks") != blocks:
            raise RuntimeError(f"recipe {RECIPE_ID} app-home blocks changed on {step_as} (twin drift?)")
    if_nodes = [n for n in _walk_nodes(raw) if n.get("keyword") == "if"]
    if len(if_nodes) != 1:
        raise RuntimeError(f"recipe {RECIPE_ID} no longer has exactly one IF")
    conditions = (if_nodes[0].get("input") or {}).get("conditions") or [{}]
    if (
        len(conditions) != 1
        or str(conditions[0].get("operand") or "") != "greater_than"
        or str(conditions[0].get("rhs") or "") != "0"
        or "path_element_type" not in str(conditions[0].get("lhs") or "")
        or SEARCH_AS not in str(conditions[0].get("lhs") or "")
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} IF condition changed: {conditions!r}")
    dead_steps = [n for n in _walk_nodes(raw) if n.get("keyword") == "action" and n.get("skip")]
    if sorted(str(n.get("as") or "") for n in dead_steps) != sorted(DEAD_STEP_AS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} dead skip:true steps changed: "
            f"{sorted(str(n.get('as') or '') for n in dead_steps)} (twin drift?)"
        )
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "table_id": TABLE_ID,
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


def seed_121951507(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_121951507(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["lookup_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the lookup_table section; "
            f"got {sorted(seed_in.keys())}"
        )
    matched = _require_lookup_section(seed_in["lookup_table"])
    expect = data.get("expect")
    _require_expect(expect, matched)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: force_action_error would only abort "
            "the run and is not a recipe branch"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "lookup_table": deepcopy(seed_in["lookup_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_121951507(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_121951507(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    initial_snapshot = _snapshot(ctx)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx)
    # Cleanup per the cleanup principle: the lookup table is a per-variant mock
    # the seed fully overwrites and the recipe only READS it; views.publish
    # overwrites the SAME member's App Home tab on every run (idempotent live
    # surface, never re-read) — nothing persistent to clean.
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
    result["verifier"] = verify_121951507(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["app_home_opened"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly app_home_opened; "
            f"got {sorted(trigger.keys())}"
        )
    payload = trigger.get("app_home_opened")
    if not isinstance(payload, dict) or sorted(payload.keys()) != ["user"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.app_home_opened must be exactly "
            "{'user': <workspace member id>} (the only field the recipe dereferences)"
        )
    user = payload.get("user")
    if not isinstance(user, str) or not _USER_RE.fullmatch(user):
        raise RuntimeError(
            f"recipe {RECIPE_ID} app_home_opened.user must be a Slack user id: {user!r}"
        )
    if user != LIVE_MEMBER_ID:
        raise RuntimeError(
            f"recipe {RECIPE_ID} app_home_opened.user must be the proven live member "
            f"{LIVE_MEMBER_ID} ({LIVE_MEMBER_EMAIL}): users.info runs LIVE fail-fast "
            f"and the recipe pivots on profile.email (the bot U0B973TLN7N has no "
            f"profile email); got {user!r}"
        )


def _require_lookup_section(section: Any) -> int:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly table "
            f"{TABLE_ID!r} (twin guard: the twin recipe seeds a different id)"
        )
    rows = tables[TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {TABLE_ID} must be a NON-EMPTY list — the col3 "
            "exact-match is proven by decoy rows, not by an empty table"
        )
    matched = 0
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} must be an object")
        unknown = sorted(set(row.keys()) - set(ROW_FIELDS))
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} uses undeclared columns: {unknown}"
            )
        for column, value in row.items():
            if not isinstance(value, str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table row {idx}.{column} must be a string "
                    "(lookup table cells are text)"
                )
        if not str(row.get(EMAIL_COL) or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} requires a non-empty {EMAIL_COL} "
                "(Email address) — the search keys on it"
            )
        if row[EMAIL_COL] == LIVE_MEMBER_EMAIL:
            matched += 1
    return matched


def _require_expect(expect: Any, matched: int) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    outcome = expect.get("outcome")
    if outcome not in OUTCOMES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.outcome must be one of {OUTCOMES}")
    if expect.get("member_email") != LIVE_MEMBER_EMAIL:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.member_email must pin the live member email "
            f"{LIVE_MEMBER_EMAIL!r} (users.info groundtruth); got {expect.get('member_email')!r}"
        )
    if expect.get("matched_entry_count") != matched:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.matched_entry_count must equal the seeded rows "
            f"whose col3 is the live member email ({matched}); got "
            f"{expect.get('matched_entry_count')!r}"
        )
    if outcome == "admin_home":
        checks = (
            matched >= 1,
            expect.get("home_step") == ADMIN_HOME_AS,
            expect.get("home_blocks") == ADMIN_BLOCKS,
        )
        reason = "admin_home: >=1 matching row -> IF true -> 16-block admin home 2c4d9486"
    else:
        checks = (
            matched == 0,
            expect.get("home_step") == DEFAULT_HOME_AS,
            expect.get("home_blocks") == DEFAULT_BLOCKS,
        )
        reason = (
            "default_home: 0 matching rows (decoys prove the filter) -> ELSE -> "
            f"11-block default home {DEFAULT_HOME_AS}"
        )
    if not all(checks) or expect.get("executed_action_count") != 3 or expect.get("tools") != [
        "slack_bot.get_user_by_email",
        "lookup_table.search_entries",
        "slack_bot.open_bot_app_home",
    ]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with outcome {outcome!r} "
            f"({reason}): {expect!r}"
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
    return dict(ctx.tools.call("harness.lookup_table.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
