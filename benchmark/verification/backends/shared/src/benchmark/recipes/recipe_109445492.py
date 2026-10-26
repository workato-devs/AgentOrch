from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_109445492


RECIPE_ID = "109445492"
SEED_TYPE = "slack_app_home_credentials_gate_variant"
TRACK = "live_slack_app_home_publish"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "new_event"
TRIGGER_AS = "58812fc4"
GET_STEP_AS = "137a7374"
ADMIN_HOME_AS = "fef0c653"
STOP_STEP_AS = "fdc8e696"
PROGRESS_HOME_AS = "4416ee0e"
CATCH_AS = "8cf5706f"
LOG_STEP_AS = "1cebb51a"
TABLE_ID = "16911"
USER_FIELD = "af2f7fd0_ccf4_41c9_aed9_25da1e5d2a0a"
RECORD_ID_FIELD = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
RELATION_FIELD = "ab00b946_6011_467f_b615_23efd6668fd5"
ROW_FIELDS = {
    RECORD_ID_FIELD,          # Record ID
    USER_FIELD,               # user
    "a696728c_30b6_46bb_bf03_a580c6f98462",  # provider
    "2d71aeb8_dd53_4b30_b575_7474eb515d11",  # application
    "e93a33b6_657e_4c96_9388_e8e7daeb2d27",  # priority
    "dcacbe8f_976e_4201_89e0_716b168b1887",  # Hosted
    "5d328e77_69e4_48f5_89d2_58f81a8b20c0",  # Strategy
    RELATION_FIELD,           # application-link (relation object)
    "a5612739_5401_4ae7_bd07_782c1a6fb2d1",  # Created at
    "61aae604_a95e_4519_9091_bb0bf754a67f",  # Updated at
}
ADMIN_BLOCKS: list[dict[str, Any]] = [
    {
        "actions": [
            {
                "bot_command": "56203945",
                "button_title": "Admin - New Credentials",
                "style": "primary",
                "type": "button",
            }
        ],
        "block_type": "actions",
    }
]
PROGRESS_BLOCKS: list[dict[str, Any]] = [
    {
        "actions": [
            {
                "bot_command": "56251179",
                "button_title": "My Progress",
                "style": "primary",
                "type": "button",
            },
            {
                "bot_command": "56280498",
                "button_title": "Delete Progress",
                "style": "danger",
                "type": "button",
            },
        ],
        "block_type": "actions",
    }
]


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "slack_bot", "name": "new_event", "as": "58812fc4", "skip": false, "input": {"event_name": "app_home_opened"}, "block": [{"number": 2, "keyword": "try", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 3, "keyword": "action", "provider": "workato_db_table", "name": "get_records", "as": "137a7374", "skip": false, "input": {"11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "2d71aeb8-dd53-4b30-b575-7474eb515d11": "string", "5d328e77-69e4-48f5-89d2-58f81a8b20c0": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "a696728c-30b6-46bb-bf03-a580c6f98462": "string", "ab00b946-6011-467f-b615-23efd6668fd5": "relation", "af2f7fd0-ccf4-41c9-aed9-25da1e5d2a0a": "string", "dcacbe8f-976e-4201-89e0-716b168b1887": "string", "e93a33b6-657e-4c96-9388-e8e7daeb2d27": "string", "filters": [{"field_id": "af2f7fd0-ccf4-41c9-aed9-25da1e5d2a0a", "op_default": "eq", "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"58812fc4\",\"path\":[\"app_home_opened\", \"user\"]}')}"}], "limit": "100", "order_direction": "asc", "table_id": "16911"}, "block": []}, {"number": 4, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"137a7374\",\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}", "operand": "less_than", "rhs": "1"}], "operand": "and", "type": "compound"}, "block": [{"number": 5, "keyword": "action", "provider": "slack_bot", "name": "open_bot_app_home", "as": "fef0c653", "skip": false, "input": {"blocks": [{"actions": [{"bot_command": "56203945", "button_title": "Admin - New Credentials", "style": "primary", "type": "button"}], "block_type": "actions"}], "user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"58812fc4\",\"path\":[\"app_home_opened\", \"user\"]}')}"}, "block": []}, {"number": 6, "keyword": "stop", "provider": "", "name": "", "as": "fdc8e696", "skip": false, "input": {"stop_with_error": "false"}, "block": []}]}, {"number": 7, "keyword": "action", "provider": "slack_bot", "name": "open_bot_app_home", "as": "4416ee0e", "skip": false, "input": {"blocks": [{"actions": [{"bot_command": "56251179", "button_title": "My Progress", "style": "primary", "type": "button"}, {"bot_command": "56280498", "button_title": "Delete Progress", "style": "danger", "type": "button"}], "block_type": "actions"}], "user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"58812fc4\",\"path\":[\"app_home_opened\", \"user\"]}')}"}, "block": []}, {"number": 8, "keyword": "catch", "provider": "", "name": "", "as": "8cf5706f", "skip": false, "input": {"max_retry_count": "0", "retry_interval": "2"}, "block": [{"number": 9, "keyword": "action", "provider": "logger", "name": "log_message", "as": "1cebb51a", "skip": false, "input": {"message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"8cf5706f\",\"path\":[\"type\"]}')} - #{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"8cf5706f\",\"path\":[\"message\"]}')}", "user_logs_enabled": "false"}, "block": []}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (GET_STEP_AS, "workato_db_table", "get_records"),
    (ADMIN_HOME_AS, "slack_bot", "open_bot_app_home"),
    (PROGRESS_HOME_AS, "slack_bot", "open_bot_app_home"),
    (LOG_STEP_AS, "logger", "log_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "slack_bot.open_bot_app_home",
    "workato_runtime.log_message",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "slack_bot.open_bot_app_home",
]
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "outcome",
    "stopped",
    "matched_record_count",
    "home_blocks",
    "log_message",
)
OUTCOMES = ("admin_home", "progress_home", "catch_log")
_USER_RE = re.compile(r"^U[A-Z0-9]{5,12}$")


def validate_109445492(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Semantic pins on the drift-prone bits.
    get_node = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == GET_STEP_AS), None
    )
    if not isinstance(get_node, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} get_records step {GET_STEP_AS} missing")
    get_input = get_node.get("input") or {}
    if str(get_input.get("table_id") or "") != TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} table id changed")
    filters = get_input.get("filters") or []
    if (
        len(filters) != 1
        or str(filters[0].get("field_id") or "").replace("-", "_") != USER_FIELD
        or str(filters[0].get("op_default") or "") != "eq"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} user eq filter changed: {filters!r}")
    for step_as, blocks in ((ADMIN_HOME_AS, ADMIN_BLOCKS), (PROGRESS_HOME_AS, PROGRESS_BLOCKS)):
        node = next(
            (n for n in _walk_nodes(raw) if str(n.get("as") or "") == step_as), None
        )
        if not isinstance(node, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} app-home step {step_as} missing")
        if (node.get("input") or {}).get("blocks") != blocks:
            raise RuntimeError(f"recipe {RECIPE_ID} app-home blocks changed on {step_as}")
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


def seed_109445492(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_109445492(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    user = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    expect = data.get("expect")
    _require_expect_common(expect)
    outcome = expect["outcome"]
    force = data.get("force_action_error")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
    }
    if outcome == "catch_log":
        _require_catch_variant(seed_in, expect, force)
    else:
        matched = _require_home_variant(seed_in, expect, force, user, outcome)
        out["workato_db_table"] = deepcopy(seed_in["workato_db_table"])
        out["matched_record_count"] = matched
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_109445492(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_109445492(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if expect.get("outcome") != "catch_log" and not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    initial_snapshot = _snapshot(ctx)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx)
    # Cleanup per the cleanup principle: the db table is a per-variant mock the
    # seed fully overwrites, and views.publish overwrites the SAME user's App
    # Home tab on every run (idempotent surface, never re-read) — no cleanup
    # step exists to run.
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": expect,
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_109445492(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> str:
    if sorted(trigger.keys()) != ["app_home_opened"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly app_home_opened; "
            f"got {sorted(trigger.keys())}"
        )
    payload = trigger.get("app_home_opened")
    if not isinstance(payload, dict) or sorted(payload.keys()) != ["user"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.app_home_opened must be exactly "
            "{'user': <workspace user id>} (the only field the recipe dereferences)"
        )
    user = payload.get("user")
    if not isinstance(user, str) or not _USER_RE.fullmatch(user):
        raise RuntimeError(
            f"recipe {RECIPE_ID} app_home_opened.user must be a Slack user id "
            f"(U...); views.publish runs LIVE against it and it must be a real "
            f"benchmark-workspace member: {user!r}"
        )
    return user


def _require_expect_common(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("outcome") not in OUTCOMES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.outcome must be one of {OUTCOMES}")


def _require_home_variant(
    seed_in: dict[str, Any],
    expect: dict[str, Any],
    force: Any,
    user: str,
    outcome: str,
) -> int:
    if force is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} home variants must not force an action error")
    if sorted(seed_in.keys()) != ["workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} home variants must seed exactly the workato_db_table "
            f"section; got {sorted(seed_in.keys())}"
        )
    matched = _require_db_table_section(seed_in["workato_db_table"], user)
    if expect.get("matched_record_count") != matched:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.matched_record_count must equal the seeded rows "
            f"matching the trigger user ({matched}); got {expect.get('matched_record_count')!r}"
        )
    if outcome == "admin_home":
        checks = (
            matched == 0,
            expect.get("stopped") is True,
            expect.get("home_blocks") == ADMIN_BLOCKS,
            expect.get("log_message") is None,
            expect.get("executed_action_count") == 2,
            expect.get("tools")
            == ["workato_db_table.get_records", "slack_bot.open_bot_app_home"],
        )
        reason = (
            "admin_home: 0 matching rows (decoys prove the filter) -> admin publish -> "
            "STOP before step 4416ee0e"
        )
    else:  # progress_home
        checks = (
            matched >= 1,
            expect.get("stopped") is False,
            expect.get("home_blocks") == PROGRESS_BLOCKS,
            expect.get("log_message") is None,
            expect.get("executed_action_count") == 2,
            expect.get("tools")
            == ["workato_db_table.get_records", "slack_bot.open_bot_app_home"],
        )
        reason = "progress_home: >=1 matching row -> IF false -> 2-button publish, no stop"
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with outcome {outcome!r} "
            f"({reason}): {expect!r}"
        )
    return matched


def _require_catch_variant(seed_in: dict[str, Any], expect: dict[str, Any], force: Any) -> None:
    if not isinstance(force, dict) or str(force.get("step_as") or "") != GET_STEP_AS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch is not naturally reachable: catch variants "
            f"must declare force_action_error.step_as == {GET_STEP_AS!r}"
        )
    error = str(force.get("error") or "")
    if not error.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error.error must be explicit")
    if sorted(seed_in.keys()) != []:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variants must not seed any section (the forced "
            f"error fires before the db read; nothing else runs); got {sorted(seed_in.keys())}"
        )
    checks = (
        expect.get("stopped") is False,
        expect.get("matched_record_count") is None,
        expect.get("home_blocks") is None,
        expect.get("log_message") == f"RawRecipeExecutionError - {error}",
        expect.get("executed_action_count") == 1,
        expect.get("tools") == [],
        expect.get("tool_expectations") == [],
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch expect block is inconsistent: the log message "
            f"must pin the ENGINE rendering 'RawRecipeExecutionError - {error}', with "
            f"1 action and zero registry tools; got {expect!r}"
        )


def _require_db_table_section(section: Any, user: str) -> int:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly "
            f"table {TABLE_ID!r}"
        )
    rows = tables[TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {TABLE_ID} must be a NON-EMPTY list — the eq "
            "filter is proven by decoy rows, not by an empty table"
        )
    matched = 0
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} must be an object")
        unknown = sorted(set(row.keys()) - ROW_FIELDS)
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} uses undeclared field ids: {unknown}"
            )
        for key in (RECORD_ID_FIELD, USER_FIELD):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table row {idx} requires non-empty string "
                    f"{key!r}"
                )
        relation = row.get(RELATION_FIELD)
        if relation is not None and not isinstance(relation, dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} relation field must be an object"
            )
        if row[USER_FIELD] == user:
            matched += 1
    return matched


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
    return dict(ctx.tools.call("harness.workato_db_table.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
