from __future__ import annotations

import datetime
import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_98906732


RECIPE_ID = "98906732"
SEED_TYPE = "wrksm_platform_requests_retention_sweep_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "a0b7f806"
TABLE_ID = "12254"

# clock.scheduled_event (as a0b7f806, daily 08:00 Asia/Singapore -- payload-less;
# the recipe reads only `today`, so every variant pins seed `now` and mirrors it
# in trigger_input.scheduled_time):
#   2  declare_variable 424312ba page_limit = "200" (integer_conversion -> 200),
#      next_page_token nil
#   REPEAT 3 (do-while over data-table pages):
#     4  workato_db_table.get_records 9f52e0da table 12254
#        '[WRKSM] Platform Requests & Responses', filter Status(cf556506...)
#        ne 'new', order Created-at asc (mock serves seeded order; seeds MUST
#        be ascending), limit = page_limit pill (mock ignores limit),
#        continuation_token = '=next_page_token.presence or skip' (SKIP omits
#        the arg on the first page)
#     FOREACH 5 (as 50356e1e) over records:
#       IF 6: '=(created_at.to_date - today).to_i + 1' greater_than '90'
#         -- AUTHOR-INVERTED LOGIC replayed faithfully: the comment says "more
#         than 90 days since request was made" but created-minus-today is only
#         > 90 when Created at is >= 90 days IN THE FUTURE of seed today
#         (boundary: today+90d -> 91 -> true; today+89d -> 90 -> false).
#         Past-dated rows are NEVER deleted.
#         7  workato_db_table.delete_record d9f0502a record_id = foreach
#            Record ID (11fbe9a6...)
#         8  logger.log_message 2b814176 INFO '="[WRKSM] DELETED REQUEST
#            RECORD\n\n" + item.to_s' -- engine-canonical rendering: the \n
#            escapes DECODE to real newlines (interpolation-aware double-quoted
#            literal in arithmetic) and the whole foreach item renders as a
#            Python dict repr including the mock bookkeeping keys (_row_id,
#            _created_by); expects pin the exact string
#         9  workato_list.accumulate_list_items a8da182e 'Jobs Report'
#            {request_id, secondary_id, workspace_id, datacenter_alpha_2_code}
#     10 update_variables 6608ff7f next_page_token = '=step-4
#        continuation_token.presence or clear' (clear -> "")
#     WHILE 11: step-4 continuation_token present
#
# Backends: workato_db_table 12254 is a Workato-internal mock seeded per
# variant (deletes are mock-state only -> per-variant isolation IS the
# cleanup); logger / workato_list / workato_variable are in-executor mocks.
# Pagination is the deterministic seeded mock: continuation_tokens mapping
# {"": "<tok>"} serves a token on the first page only, and the mock re-serves
# the full remaining (filtered) table on every page -- the two-page variant
# keeps per-page work disjoint because page 1 DELETES its matched row.
#
# TWIN: 98906320 is byte-identical except table_id 12253 (diff-verified);
# both modules keep the same table schema/column ids.

_RAW_PIN_JSON = r"""{"as": "a0b7f806", "block": [{"as": "424312ba", "block": [], "input": {"variables": {"data": {"page_limit": "200"}, "schema": "[{\"name\":\"page_limit\",\"type\":\"integer\",\"optional\":true,\"label\":\"Page Limit\",\"details\":{\"real_name\":\"Page Limit\"},\"control_type\":\"integer\"},{\"name\":\"next_page_token\",\"type\":\"string\",\"optional\":true,\"label\":\"Next Page Token\",\"details\":{\"real_name\":\"Next Page Token\"},\"control_type\":\"text\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 2, "provider": "workato_variable", "skip": false}, {"as": "a66ab964", "block": [{"as": "9f52e0da", "block": [], "input": {"11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "1c6304b6-b7ed-476b-8850-947626a2ccae": "string", "45fc828d-eb7d-40c1-a620-15b8c087b897": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "6491892d-d0c8-43e1-ae0e-ec83a7957676": "string", "8fbb1114-497b-4609-a2f4-e976909b3eac": "string", "917e9b64-6352-445a-90e6-fac398123f0f": "string", "9d257319-36bb-47e2-9854-bfc144638f67": "string", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "c8d2d496-4303-461b-90a6-25e3e760e7ed": "string", "cf556506-9231-4779-88eb-2a1d6471fa93": "string", "continuation_token": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"424312ba\",\"path\":[\"next_page_token\"]}').presence or skip", "d2f98611-d720-4ecc-9e2e-9ab0b19a6613": "integer", "filters": [{"field_id": "cf556506-9231-4779-88eb-2a1d6471fa93", "op_default": "ne", "value_default": "new"}], "limit": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"424312ba\",\"path\":[\"page_limit\"]}')}", "order_by_field_id": "a5612739-5401-4ae7-bd07-782c1a6fb2d1", "order_direction": "asc", "table_id": "12254"}, "keyword": "action", "name": "get_records", "number": 4, "provider": "workato_db_table", "skip": false}, {"as": "50356e1e", "block": [{"as": "", "block": [{"as": "d9f0502a", "block": [], "input": {"record_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"50356e1e\",\"path\":[\"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}", "table_id": "12254"}, "keyword": "action", "name": "delete_record", "number": 7, "provider": "workato_db_table", "skip": false}, {"as": "2b814176", "block": [], "input": {"log_level": "INFO", "message": "=\"[WRKSM] DELETED REQUEST RECORD\\n\\n\" + _dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"50356e1e\",\"path\":[]}').to_s", "user_logs_enabled": true}, "keyword": "action", "name": "log_message", "number": 8, "provider": "logger", "skip": false}, {"as": "a8da182e", "block": [], "input": {"list_item": {"data": {"datacenter_alpha_2_code": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"50356e1e\",\"path\":[\"9d257319_36bb_47e2_9854_bfc144638f67\"]}')}", "request_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"50356e1e\",\"path\":[\"1c6304b6_b7ed_476b_8850_947626a2ccae\"]}')}", "secondary_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"50356e1e\",\"path\":[\"8fbb1114_497b_4609_a2f4_e976909b3eac\"]}')}", "workspace_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"50356e1e\",\"path\":[\"d2f98611_d720_4ecc_9e2e_9ab0b19a6613\"]}')}"}, "schema": "[{\"control_type\":\"text\",\"label\":\"Request Id\",\"name\":\"request_id\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"Request Id\"}},{\"control_type\":\"text\",\"label\":\"Secondary Id\",\"name\":\"secondary_id\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"Secondary Id\"}},{\"control_type\":\"integer\",\"label\":\"Workspace Id\",\"parse_output\":\"integer_conversion\",\"name\":\"workspace_id\",\"type\":\"integer\",\"optional\":true,\"details\":{\"real_name\":\"Workspace Id\"}},{\"control_type\":\"text\",\"label\":\"Datacenter Alpha2Code\",\"name\":\"datacenter_alpha_2_code\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"Datacenter Alpha2Code\"}}]"}, "name": "Jobs Report"}, "keyword": "action", "name": "accumulate_list_items", "number": 9, "provider": "workato_list", "skip": false}], "input": {"conditions": [{"lhs": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"50356e1e\",\"path\":[\"a5612739_5401_4ae7_bd07_782c1a6fb2d1\"]}').to_date - today).to_i + 1", "operand": "greater_than", "rhs": "90"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 6, "provider": "", "skip": false}], "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"9f52e0da\",\"path\":[\"records\"]}')}"}, "keyword": "foreach", "name": "", "number": 5, "provider": "", "repeat_mode": "simple", "skip": false, "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"9f52e0da\",\"path\":[\"records\"]}')}"}, {"as": "6608ff7f", "block": [], "input": {"name": "28ff1af7-874c-49fc-b252-b9c7eccc198c:424312ba:next_page_token", "next_page_token": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"9f52e0da\",\"path\":[\"continuation_token\"]}').presence or clear"}, "keyword": "action", "name": "update_variables", "number": 10, "provider": "workato_variable", "skip": false}, {"as": "", "block": [], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"9f52e0da\",\"path\":[\"continuation_token\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "while_condition", "name": "", "number": 11, "provider": "", "skip": false}], "input": {}, "keyword": "repeat", "name": "", "number": 3, "provider": "", "skip": false}], "input": {"time_unit": "days", "timezone": "Asia/Singapore", "trigger_at": "08:00:00", "trigger_every": "1"}, "keyword": "trigger", "name": "scheduled_event", "number": 1, "provider": "clock", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

RECORD_ID_FIELD = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
REQUEST_ID_FIELD = "1c6304b6_b7ed_476b_8850_947626a2ccae"
SECONDARY_ID_FIELD = "8fbb1114_497b_4609_a2f4_e976909b3eac"
COMMAND_FIELD = "917e9b64_6352_445a_90e6_fac398123f0f"
DATACENTER_FIELD = "9d257319_36bb_47e2_9854_bfc144638f67"
WORKSPACE_ID_FIELD = "d2f98611_d720_4ecc_9e2e_9ab0b19a6613"
STATUS_FIELD = "cf556506_9231_4779_88eb_2a1d6471fa93"
REQUEST_JOB_FIELD = "6491892d_d0c8_43e1_ae0e_ec83a7957676"
RESPONSE_JOB_FIELD = "c8d2d496_4303_461b_90a6_25e3e760e7ed"
RESPONSE_PAYLOAD_FIELD = "45fc828d_eb7d_40c1_a620_15b8c087b897"
CREATED_AT_FIELD = "a5612739_5401_4ae7_bd07_782c1a6fb2d1"
UPDATED_AT_FIELD = "61aae604_a95e_4519_9091_bb0bf754a67f"
ROW_FIELDS = (
    RECORD_ID_FIELD,
    REQUEST_ID_FIELD,
    SECONDARY_ID_FIELD,
    COMMAND_FIELD,
    DATACENTER_FIELD,
    WORKSPACE_ID_FIELD,
    STATUS_FIELD,
    REQUEST_JOB_FIELD,
    RESPONSE_JOB_FIELD,
    RESPONSE_PAYLOAD_FIELD,
    CREATED_AT_FIELD,
    UPDATED_AT_FIELD,
)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("424312ba", "workato_variable", "declare_variable"),
    ("9f52e0da", "workato_db_table", "get_records"),
    ("d9f0502a", "workato_db_table", "delete_record"),
    ("2b814176", "logger", "log_message"),
    ("a8da182e", "workato_list", "accumulate_list_items"),
    ("6608ff7f", "workato_variable", "update_variables"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_db_table.get_records",
    "workato_db_table.delete_record",
    "workato_runtime.log_message",
    "workato_runtime.accumulate_list_items",
    "workato_runtime.update_variables",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.delete_record",
]
EXPECTED_TRIGGER_INPUT = {
    "time_unit": "days",
    "timezone": "Asia/Singapore",
    "trigger_at": "08:00:00",
    "trigger_every": "1",
}


def validate_98906732(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if raw.get("input") != EXPECTED_TRIGGER_INPUT:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger schedule changed: {raw.get('input')}")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    for action in actions:
        if action.get("provider") == "workato_db_table":
            if str((action.get("input") or {}).get("table_id") or "") != TABLE_ID:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} step {action.get('number')} table_id changed"
                )
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


def seed_98906732(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_98906732(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    now = _require_pinned_time(data, trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the workato_db_table section; "
            f"got {sorted(seed_in.keys())}"
        )
    _require_db_section(seed_in["workato_db_table"])
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "now": now,
        "expect": deepcopy(expect),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_98906732(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_98906732(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    if not str(seed.get("now") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing pinned now")
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
    result["verifier"] = verify_98906732(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_pinned_time(data: dict[str, Any], trigger: dict[str, Any]) -> str:
    if sorted(trigger.keys()) != ["scheduled_time"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly scheduled_time; "
            f"got {sorted(trigger.keys())}"
        )
    scheduled = trigger.get("scheduled_time")
    now = data.get("now")
    for label, value in (("trigger_input.scheduled_time", scheduled), ("now", now)):
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"recipe {RECIPE_ID} {label} must be a non-empty string")
        try:
            parsed = datetime.datetime.fromisoformat(value)
        except ValueError as exc:
            raise RuntimeError(f"recipe {RECIPE_ID} {label} is not ISO-8601: {value!r}") from exc
        if parsed.tzinfo is None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {label} must carry an explicit UTC offset "
                "(the schedule is timezone-pinned to Asia/Singapore)"
            )
    if scheduled != now:
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires now == trigger_input.scheduled_time so `today` "
            f"is unambiguous; got now={now!r} scheduled_time={scheduled!r}"
        )
    return str(now)


def _require_db_section(section: Any) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.workato_db_table must be an object")
    unknown = sorted(set(section.keys()) - {"tables", "continuation_tokens"})
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.workato_db_table has unknown keys: {unknown}")
    tables = section.get("tables")
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly table {TABLE_ID!r}"
        )
    rows = tables[TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {TABLE_ID} seed must be a non-empty row list "
            "(zero-match variants seed rows the Status filter excludes)"
        )
    seen_ids: set[str] = set()
    created_values: list[str] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} must be an object")
        if sorted(row.keys()) != sorted(ROW_FIELDS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} must carry exactly the 12 seeded columns "
                "(the logger pins the whole-row rendering); "
                f"got {sorted(row.keys())}"
            )
        for field in ROW_FIELDS:
            value = row[field]
            if field == WORKSPACE_ID_FIELD:
                if not isinstance(value, int) or isinstance(value, bool):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} table row {idx} Workspace ID must be an integer"
                    )
                continue
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table row {idx} requires a non-empty string {field!r}"
                )
        record_id = row[RECORD_ID_FIELD]
        if record_id in seen_ids:
            raise RuntimeError(f"recipe {RECIPE_ID} duplicate Record ID {record_id!r}")
        seen_ids.add(record_id)
        for field in (CREATED_AT_FIELD, UPDATED_AT_FIELD):
            try:
                datetime.datetime.fromisoformat(str(row[field]).replace("Z", "+00:00"))
            except ValueError as exc:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table row {idx} {field} is not an ISO timestamp"
                ) from exc
        created_values.append(str(row[CREATED_AT_FIELD]))
    if created_values != sorted(created_values):
        raise RuntimeError(
            f"recipe {RECIPE_ID} table rows must be seeded ascending by Created at "
            "(the recipe orders by Created at asc; the mock serves seeded order)"
        )
    tokens = section.get("continuation_tokens")
    if tokens is not None:
        if not isinstance(tokens, dict) or sorted(tokens.keys()) != [TABLE_ID]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed continuation_tokens must declare exactly table {TABLE_ID!r}"
            )
        mapping = tokens[TABLE_ID]
        if not isinstance(mapping, dict) or not mapping:
            raise RuntimeError(
                f"recipe {RECIPE_ID} continuation_tokens[{TABLE_ID!r}] must be a non-empty "
                "incoming-token -> next-token mapping (\"\" keys the first page)"
            )
        for key, value in mapping.items():
            if not isinstance(key, str) or not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} continuation_tokens mapping must be str -> non-empty str"
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
    return ctx.tools.call("harness.workato_db_table.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
