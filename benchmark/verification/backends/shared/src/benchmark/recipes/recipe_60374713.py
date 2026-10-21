from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import (
    RawWorkatoRuntime,
    RuntimeState,
    _smart_list_key,
    field_value,
    input_obj,
    resolve_smart_list_sql,
)
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_60374713
from .salesforce_recipe_utils import collect_actions
from .snowflake_live_recipe_utils import ground_truth, seed_live_snowflake


RECIPE_ID = "60374713"
SEED_TYPE = "snowflake_updated_employee_dupe_id_slack_alert_variant"
TRACK = "snowflake_dupe_id_smart_list_slack_alert"
TRIGGER_PROVIDER = "snowflake"
TRIGGER_NAME = "updated_row"
TRIGGER_TABLE = "PUBLIC.EMPLOYEE"
TRIGGER_PRIMARY_KEY = "EMAIL"
TRIGGER_SORT_COLUMN = "MODIFIED_AT"
CONVERSATION_ID = "G013R8QUFRB"
# The trigger row is never dereferenced by the steps (the recipe rescans the
# whole table), but a faithful updated-row payload is still required.
REQUIRED_TRIGGER_FIELDS = ("id", "email", "modified_at")
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_smart_list", "query_list"),      # 2  CREATE TABLE DUPE_EMP
    ("snowflake", "search_rows_sql"),          # 3  GROUP BY ID HAVING COUNT > 1
    ("snowflake", "search_rows"),              # 5  rows WHERE ID = <dup id>
    ("workato_smart_list", "query_list"),      # 7  INSERT INTO DUPE_EMP
    ("workato_smart_list", "query_list"),      # 8  SELECT DISTINCT ID
    ("workato_variable", "declare_variable"),  # 9  conversation_id
    ("slack_bot", "post_bot_message"),         # 11 block-kit header
    ("workato_smart_list", "query_list"),      # 13 SELECT * WHERE ID = <id>
    ("slack_bot", "post_bot_message"),         # 14 threaded context reply
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_smart_list.query_list",
    "snowflake.search_rows_sql",
    "snowflake.search_rows",
    "workato_runtime.declare_variable",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "snowflake.search_rows",
    "slack.post_message",
]

# The shared engine's smart_list_query does not parse a bare
# "SELECT DISTINCT <col> FROM <table>" (no WHERE); this raw recipe needs
# exactly that one form at step 8. The extension lives here (module-local
# runtime subclass) because harness files are frozen for this batch; fold it
# into raw_executor.smart_list_query when the engine is next extended.
_SELECT_DISTINCT_RE = re.compile(
    r"SELECT\s+DISTINCT\s+([A-Za-z_][A-Za-z0-9_]*)\s+FROM\s+([A-Za-z_][A-Za-z0-9_ ]*)",
    flags=re.I,
)


class _Runtime60374713(RawWorkatoRuntime):
    def workato_smart_list_query(
        self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        sql = resolve_smart_list_sql(raw_input.get("sql"), self.ctx, state)
        text = " ".join(str(sql or "").split()).rstrip(" ;")
        match = _SELECT_DISTINCT_RE.fullmatch(text)
        if not match:
            return super().workato_smart_list_query(node, _ctx, state)
        column = match.group(1)
        source_rows = self.smart_lists.get(_smart_list_key(match.group(2)), [])
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        for row in source_rows:
            value = field_value(row, column)
            marker = str(value)
            if marker in seen:
                continue
            seen.add(marker)
            # Faithful to Workato: SELECT DISTINCT <col> returns only that
            # column (the declared 2-column result schema does NOT backfill
            # EMAIL here), in first-occurrence order.
            rows.append({column: value})
        result = {
            "ok": True,
            "rows": rows,
            "row_count": len(rows),
            "count": len(rows),
            "columns": {column: column},
            "column_aliases": {column: column},
        }
        return "workato_smart_list.query_list", {"sql": sql}, result


def validate_60374713(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    trigger_config = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if str(trigger_config.get("table") or "") != TRIGGER_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger table mapping changed")
    if str(trigger_config.get("primary_key") or "") != TRIGGER_PRIMARY_KEY:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger primary key mapping changed")
    if str(trigger_config.get("sort_column") or "") != TRIGGER_SORT_COLUMN:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger sort column mapping changed")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    create_sql = str((actions[0].get("input") or {}).get("sql") or "")
    if "CREATE TABLE DUPE_EMP" not in create_sql:
        raise RuntimeError(f"recipe {RECIPE_ID} DUPE_EMP create mapping changed")
    dup_sql = str((actions[1].get("input") or {}).get("sql") or "")
    for fragment in ("FROM EMPLOYEE E", "GROUP BY ID", "HAVING COUNT > 1"):
        if fragment not in dup_sql:
            raise RuntimeError(f"recipe {RECIPE_ID} duplicate-count SQL mapping changed")
    search_input = actions[2].get("input") if isinstance(actions[2].get("input"), dict) else {}
    if str(search_input.get("table") or "") != TRIGGER_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} snowflake search table changed")
    if not str(search_input.get("where") or "").startswith("ID = '#{"):
        raise RuntimeError(f"recipe {RECIPE_ID} snowflake search WHERE mapping changed")
    insert_sql = str((actions[3].get("input") or {}).get("sql") or "")
    if not insert_sql.startswith("INSERT INTO DUPE_EMP"):
        raise RuntimeError(f"recipe {RECIPE_ID} DUPE_EMP insert mapping changed")
    distinct_sql = str((actions[4].get("input") or {}).get("sql") or "")
    if distinct_sql != "SELECT DISTINCT ID FROM DUPE_EMP":
        raise RuntimeError(f"recipe {RECIPE_ID} DUPE_EMP distinct mapping changed")
    variables = (actions[5].get("input") or {}).get("variables") or {}
    declared = variables.get("data") if isinstance(variables, dict) else {}
    if not isinstance(declared, dict) or declared.get("conversation_id") != CONVERSATION_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} conversation_id mapping changed")
    header_input = actions[6].get("input") if isinstance(actions[6].get("input"), dict) else {}
    if "e979bc58" not in str(header_input.get("channel") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} header channel mapping changed")
    detail_input = actions[8].get("input") if isinstance(actions[8].get("input"), dict) else {}
    advanced = detail_input.get("advanced") if isinstance(detail_input.get("advanced"), dict) else {}
    if "d0a7c06b" not in str(advanced.get("thread_ts") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} thread_ts mapping changed")
    detail_blocks = detail_input.get("blocks") or []
    detail_text = str(((detail_blocks[0].get("elements") or [{}])[0] or {}).get("text") or "") if detail_blocks else ""
    if "format_map" not in detail_text or "d08b3cfc" not in detail_text:
        raise RuntimeError(f"recipe {RECIPE_ID} threaded detail text mapping changed")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": _action_summary(actions),
    }


def seed_60374713(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_60374713(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    for required_field in REQUIRED_TRIGGER_FIELDS:
        if str(trigger.get(required_field) or "").strip() == "":
            raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing {required_field}")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    snowflake_seed = seed_in.get("snowflake_live")
    tables = snowflake_seed.get("tables") if isinstance(snowflake_seed, dict) else None
    if not isinstance(tables, dict) or TRIGGER_TABLE not in tables:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must define snowflake_live.tables[{TRIGGER_TABLE!r}]"
        )
    table_spec = tables.get(TRIGGER_TABLE) or {}
    declared_columns = table_spec.get("columns") if isinstance(table_spec, dict) else None
    if not isinstance(declared_columns, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed must declare explicit EMPLOYEE columns")
    for column in ("ID", "EMAIL", "MODIFIED_AT"):
        if column not in declared_columns:
            raise RuntimeError(f"recipe {RECIPE_ID} EMPLOYEE seed missing column {column}")
    provision = seed_live_snowflake(RECIPE_ID, data, ctx)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "snowflake_live": deepcopy(provision["state"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_60374713(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_60374713(raw)
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        raw_execution = _Runtime60374713(ctx, seed).execute(raw)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("snowflake_live"), dict):
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
            "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": {"snowflake_live": snowflake_cleanup},
            "ground_truth": ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_60374713(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("snowflake_live"), dict):
        out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    return out


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")}
        for a in actions
    ]
