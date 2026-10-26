from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import (
    MISSING,
    RawRecipeExecutionError,
    RawWorkatoRuntime,
    as_list,
    input_obj,
    resolve_value,
    step_key,
)
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_127934002


RECIPE_ID = "127934002"
SEED_TYPE = "recipe_function_data_ingestion_jobs_crud_variant"
TRACK = "workato_recipe_function_db_table_crud_router"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TABLE_ID = "45816"
METHOD_UPCASE_FORMULA = "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"1d1202b1\",\"path\":[\"parameters\",\"method\"]}').upcase"
FIELD_ID = "4352e364-c951-49a5-a86d-7bd8f7028d04"
FIELD_JOB_URL = "fa3a22c7-a57f-440f-a04e-f94ab836f09e"
FIELD_CREATE_DATE = "20506d23-9502-4b97-93b8-1b42067deeeb"
RECORD_ID_COLUMN = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
PUT_FOREACH_AS = "4d904547"
DELETE_FOREACH_AS = "c3886afe"
PUT_COUNT_FOREACH_META_PILL = "#{_dp('{\"pill_type\":\"foreach_meta\",\"provider\":\"foreach\",\"line\":\"4d904547\",\"key\":\"size\"}')}"
UPDATE_RECORD_ID_PILL = "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4d904547\",\"path\":[\"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}"
DELETE_RECORD_ID_PILL = "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"c3886afe\",\"path\":[\"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}"
COLUMN_TO_ENTRY_FIELD: dict[str, str] = {
    "4352e364_c951_49a5_a86d_7bd8f7028d04": "id",
    "3b9e1c92_c3b0_4302_91db_48bf6198de64": "dataSource",
    "75b45e23_99d1_4461_af21_0412bf1ded62": "type",
    "085e9f3c_adb9_4626_be9b_47b5ba1d8f9f": "frequency",
    "7f42d2ba_b5b4_4799_aeb3_953f99cfd322": "status",
    "20506d23_9502_4b97_93b8_1b42067deeeb": "createDate",
    "26123e39_eafd_4c18_b818_5a8c32cc3f81": "lastUpdateDateTime",
    "fa3a22c7_a57f_440f_a04e_f94ab836f09e": "jobURL",
    "a1dde651_a55c_4792_9fda_b0eec436bec3": "comments",
}
EXPECTED_ADD_PARAMETERS: dict[str, str] = {
    column: (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"1d1202b1\","
        "\"path\":[\"parameters\", \"entries\", {\"path_element_type\": \"current_item\"}, \"" + field + "\"]}')}"
    )
    for column, field in COLUMN_TO_ENTRY_FIELD.items()
}
EXPECTED_UPDATE_PARAMETERS: dict[str, str] = {
    column: (
        "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"1d1202b1\","
        "\"path\":[\"parameters\",\"entries\",{\"path_element_type\":\"current_item\"},\"" + field + "\"]}').presence"
    )
    for column, field in COLUMN_TO_ENTRY_FIELD.items()
}
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_db_table", "get_records"),          # 4  GET all
    ("workato_recipe_function", "return_result"),  # 5
    ("workato_db_table", "get_records"),          # 7  GET by id
    ("workato_recipe_function", "return_result"),  # 8
    ("workato_db_table", "add_record"),           # 10 POST (first entry only)
    ("workato_recipe_function", "return_result"),  # 11
    ("workato_db_table", "get_records"),          # 13 PUT lookup by Job URL
    ("workato_db_table", "update_record"),        # 15 PUT per matched row
    ("workato_recipe_function", "return_result"),  # 16
    ("workato_db_table", "get_records"),          # 18 DELETE lookup by Create Date
    ("workato_db_table", "delete_record"),        # 20 DELETE per matched row
    ("workato_recipe_function", "return_result"),  # 21
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
    "workato_db_table.update_record",
    "workato_db_table.delete_record",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
    "workato_db_table.update_record",
    "workato_db_table.delete_record",
    "workato_recipe_function.return_result",
]
SUPPORTED_METHODS = {"GET", "POST", "PUT", "DELETE"}


_NO_MATCH = object()
_FOREACH_META_PILL_RE = re.compile(r"\A#\{_dp\('(\{[^']*\})'\)\}\Z")


class _Runtime127934002(RawWorkatoRuntime):
    def execute_foreach(self, node: dict[str, Any], state: Any) -> None:
        raw_input = input_obj(node)
        source = resolve_value(raw_input.get("source"), self.ctx, state)
        if source is not MISSING and node.get("repeat_mode") != "batch":
            step_id = step_key(node, len(state.trace))
            state.foreach_meta.setdefault(step_id, {"size": len(as_list(source))})
        super().execute_foreach(node, state)

    def workato_return_result(
        self, node: dict[str, Any], _ctx: RecipeContext, state: Any
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        raw_result = raw_input.get("result")
        if isinstance(raw_result, dict):
            patched: dict[str, Any] = {}
            changed = False
            for key, raw_value in raw_result.items():
                resolved = self._resolve_foreach_meta_pill(raw_value, state)
                if resolved is _NO_MATCH:
                    patched[str(key)] = raw_value
                else:
                    patched[str(key)] = resolved
                    changed = True
            if changed:
                node = dict(node)
                node["input"] = dict(raw_input)
                node["input"]["result"] = patched
        return super().workato_return_result(node, _ctx, state)

    def _resolve_foreach_meta_pill(self, raw_value: Any, state: Any) -> Any:
        if not isinstance(raw_value, str):
            return _NO_MATCH
        match = _FOREACH_META_PILL_RE.fullmatch(raw_value)
        if not match:
            return _NO_MATCH
        try:
            pill = json.loads(match.group(1))
        except json.JSONDecodeError:
            return _NO_MATCH
        if pill.get("pill_type") != "foreach_meta":
            return _NO_MATCH
        line = str(pill.get("line") or "")
        key = str(pill.get("key") or "")
        meta = state.foreach_meta.get(line)
        if not isinstance(meta, dict) or key not in meta:
            raise RawRecipeExecutionError(
                f"foreach_meta pill {line}.{key} has no recorded loop metadata"
            )
        return meta[key]


def validate_127934002(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != "1d1202b1":
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')}")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    for action in actions:
        table_id = str((action.get("input") or {}).get("table_id") or "")
        if action.get("provider") == "workato_db_table" and table_id != TABLE_ID:
            raise RuntimeError(
                f"recipe {RECIPE_ID} step {action.get('number')} no longer targets table {TABLE_ID}: {table_id}"
            )
    method_ifs = {
        node.get("number"): node
        for node in _collect_ifs(raw)
        if node.get("number") in {2, 9, 12, 17}
    }
    for number, rhs in ((2, "GET"), (9, "POST"), (12, "PUT"), (17, "DELETE")):
        conditions = ((method_ifs.get(number) or {}).get("input") or {}).get("conditions") or []
        if (
            len(conditions) != 1
            or str(conditions[0].get("lhs") or "") != METHOD_UPCASE_FORMULA
            or str(conditions[0].get("operand") or "") != "equals_to"
            or str(conditions[0].get("rhs") or "") != rhs
        ):
            raise RuntimeError(f"recipe {RECIPE_ID} method router IF #{number} changed: {conditions}")
    entries_size_if = next((node for node in _collect_ifs(raw) if node.get("number") == 3), None)
    size_conditions = ((entries_size_if or {}).get("input") or {}).get("conditions") or []
    if (
        len(size_conditions) != 1
        or '"path_element_type": "size"' not in str(size_conditions[0].get("lhs") or "")
        or '"entries"' not in str(size_conditions[0].get("lhs") or "")
        or str(size_conditions[0].get("operand") or "") != "equals_to"
        or str(size_conditions[0].get("rhs") or "") != "0"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} entries.size guard changed: {size_conditions}")
    get_all, get_by_id, put_get, delete_get = actions[0], actions[2], actions[6], actions[9]
    if (get_all.get("input") or {}).get("filters") not in (None, []):
        raise RuntimeError(f"recipe {RECIPE_ID} GET-all step gained filters")
    for action, field_id, entry_field in (
        (get_by_id, FIELD_ID, "id"),
        (put_get, FIELD_JOB_URL, "jobURL"),
        (delete_get, FIELD_CREATE_DATE, "createDate"),
    ):
        filters = (action.get("input") or {}).get("filters") or []
        if len(filters) != 1 or str(filters[0].get("field_id") or "") != field_id:
            raise RuntimeError(
                f"recipe {RECIPE_ID} step {action.get('number')} filter field changed: {filters}"
            )
        value = str(filters[0].get("value_default") or "")
        if '"current_item"' not in value or f'"{entry_field}"' not in value:
            raise RuntimeError(
                f"recipe {RECIPE_ID} step {action.get('number')} filter no longer reads the "
                f"FIRST entry's {entry_field}: {value}"
            )
    add_parameters = (actions[4].get("input") or {}).get("parameters") or {}
    if add_parameters != EXPECTED_ADD_PARAMETERS:
        raise RuntimeError(f"recipe {RECIPE_ID} POST add_record mapping changed: {add_parameters}")
    update_input = actions[7].get("input") or {}
    if (update_input.get("parameters") or {}) != EXPECTED_UPDATE_PARAMETERS:
        raise RuntimeError(f"recipe {RECIPE_ID} PUT update mapping changed: {update_input.get('parameters')}")
    if str(update_input.get("record_id") or "") != UPDATE_RECORD_ID_PILL:
        raise RuntimeError(f"recipe {RECIPE_ID} PUT update record id changed: {update_input.get('record_id')}")
    delete_input = actions[10].get("input") or {}
    if str(delete_input.get("record_id") or "") != DELETE_RECORD_ID_PILL:
        raise RuntimeError(f"recipe {RECIPE_ID} DELETE record id changed: {delete_input.get('record_id')}")
    put_count = str(((actions[8].get("input") or {}).get("result") or {}).get("count") or "")
    if put_count != PUT_COUNT_FOREACH_META_PILL:
        raise RuntimeError(f"recipe {RECIPE_ID} PUT return count pill changed: {put_count}")
    post_count = str(((actions[5].get("input") or {}).get("result") or {}).get("count") or "")
    if '"entries"' not in post_count or '"path_element_type": "size"' not in post_count:
        raise RuntimeError(
            f"recipe {RECIPE_ID} POST return count no longer echoes entries.size: {post_count}"
        )
    foreach_as = {
        str(node.get("as") or ""): str((node.get("input") or {}).get("source") or "")
        for node in _collect_foreach(raw)
    }
    if set(foreach_as) != {PUT_FOREACH_AS, DELETE_FOREACH_AS}:
        raise RuntimeError(f"recipe {RECIPE_ID} foreach layout changed: {sorted(foreach_as)}")
    if '"631aa007"' not in foreach_as[PUT_FOREACH_AS] or '"0fd33de9"' not in foreach_as[DELETE_FOREACH_AS]:
        raise RuntimeError(f"recipe {RECIPE_ID} foreach sources changed: {foreach_as}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {
                "number": action.get("number"),
                "provider": action.get("provider"),
                "name": action.get("name"),
                "as": action.get("as"),
            }
            for action in actions
        ],
    }


def seed_127934002(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127934002(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires a parameters object")
    method = str(parameters.get("method") or "")
    if not method.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters.method must be non-blank"
        )
    if str(parameters.get("table") or "").strip() == "":
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires non-blank parameters.table")
    entries = parameters.get("entries")
    if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters.entries must be an explicit list of objects "
            "(an empty [] selects the GET-all branch)"
        )
    if method.upper() in {"POST", "PUT", "DELETE"} and not entries:
        raise RuntimeError(
            f"recipe {RECIPE_ID} {method.upper()} requires at least one entry: the recipe reads "
            "entries.current_item (the FIRST entry) outside any foreach"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    db_seed = seed_in.get("workato_db_table")
    tables = db_seed.get("tables") if isinstance(db_seed, dict) else None
    if not isinstance(tables, dict) or not isinstance(tables.get(TABLE_ID), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare workato_db_table.tables[{TABLE_ID!r}] "
            "explicitly (an empty table is an explicit [])"
        )
    expect = data.get("expect")
    if not isinstance(expect, dict) or "result" not in expect:
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must pin the exact expect.result return value; "
            "unsupported free-text methods must pin null for the recipe's no-op fallthrough"
        )
    if method.upper() in SUPPORTED_METHODS and not isinstance(expect.get("result"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} routed method {method.upper()} requires an object expect.result"
        )
    if method.upper() not in SUPPORTED_METHODS and expect.get("result") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} unsupported method {method!r} requires null expect.result"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(expect),
        "raw_validation": validation,
        "workato_db_table": deepcopy(db_seed),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_127934002(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127934002(raw)
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution = _Runtime127934002(ctx, seed).execute(raw)
    final_snapshot = _snapshot(ctx, seed)
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
    result["verifier"] = verify_127934002(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _collect_ifs(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "if" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_ifs(child))
    return found


def _collect_foreach(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "foreach" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_foreach(child))
    return found


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("workato_db_table"), dict):
        out.update(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
