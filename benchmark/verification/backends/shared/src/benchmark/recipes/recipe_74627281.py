from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import (
    MISSING,
    NonRecipeError,
    RawRecipeExecutionError,
    RawWorkatoRuntime,
    RuntimeState,
    eval_formula,
    input_obj,
    present,
    resolve_dp_json,
    resolve_value,
)
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_74627281
from .salesforce_recipe_utils import collect_actions
from .snowflake_live_recipe_utils import ground_truth, seed_live_snowflake


RECIPE_ID = "74627281"
SEED_TYPE = "recipe_function_subscription_log_insert_variant"
TRACK = "recipe_function_snowflake_subscription_log_insert"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
LOG_TABLE = "PUBLIC.SUBSCRIPTION_LOG"
LOG_COLUMNS = (
    "RECORD_ID",
    "SALESFORCE_ORDER_ID",
    "SALESFORCE_CONTRACT_ID",
    "NETSUITE_CUSTOMER_ID",
    "SUBSCRIPTION_START_DATE",
    "SUBSCRIPTION_END_DATE",
    "SUBSCRIPTION_CANCELLATION_DATE",
    "CHARGE_SCHEDULE_ID",
    "CURRENCY_CODE_ID",
    "CUSTOMER_REF_NO",
    "PAYMENT_TERMS_ID",
    "BILLING_PROFILE_ID",
    "SUBSIDIARY_ID",
    "SUBSCRIPTION_ID",
    "ACTION_TAKEN",
    "STATUS",
    "MODIFIED_AT",
    "CREATED_AT",
)
CATCH_FILTER_FRAGMENTS = ("Unknown error 1", "Database bridge error")
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("snowflake", "run_custom_sql"),            # 2  SHOW COLUMNS
    ("snowflake", "search_rows_sql"),           # 3  SELECT MAX(...RECORD_ID...)
    ("workato_variable", "declare_list"),       # 4  "SQL Insert"
    ("workato_variable", "declare_variable"),   # 5  column_names / created_at
    ("workato_variable", "update_variables"),   # 7  per-row field rendering
    ("workato_list", "accumulate_list_items"),  # 8  "Record IDs"
    ("workato_variable", "insert_to_list"),     # 9  insert_statement
    ("workato_variable", "declare_variable"),   # 10 insert_statements
    ("snowflake", "run_custom_sql"),            # 12 INSERT ... QUALIFY
    ("workato_recipe_function", "return_result"),  # 17
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "snowflake.search_rows_sql",
    "workato_runtime.declare_list",
    "workato_runtime.declare_variable",
    "workato_runtime.update_variables",
    "workato_runtime.accumulate_list_items",
    "workato_runtime.insert_to_list",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "snowflake.search_rows_sql",
    "workato_recipe_function.return_result",
]


_DATE_TERNARY_RE = re.compile(
    r"_dp\('(?P<pill>[^']+)'\)\.present\?\s*\?\s*"
    r"\"'#\{_dp\('(?P=pill)'\)"
    r"\.in_time_zone\(\"Etc/UTC\"\)"
    r"\.strftime\(\"%Y-%m-%d %H:%M:%S\.%L\"\)\}'\"\s*:\s*\"NULL\"",
    flags=re.S,
)


def _parse_if_node(lines: list[str], idx: int) -> tuple[tuple[Any, ...], int]:
    if idx >= len(lines):
        raise NonRecipeError("nested if formula ended unexpectedly")
    line = lines[idx]
    if line.startswith("if "):
        then_node, after_then = _parse_if_node(lines, idx + 1)
        if after_then >= len(lines) or lines[after_then] != "else":
            raise NonRecipeError(f"nested if formula requires an else branch near: {line}")
        else_node, after_else = _parse_if_node(lines, after_then + 1)
        if after_else >= len(lines) or lines[after_else] != "end":
            raise NonRecipeError(f"nested if formula missing end near: {line}")
        return ("if", line[3:].strip(), then_node, else_node), after_else + 1
    return ("expr", line), idx + 1


def _eval_if_node(node: tuple[Any, ...], ctx: RecipeContext, state: RuntimeState) -> Any:
    if node[0] == "expr":
        return eval_formula("=" + str(node[1]), ctx, state)
    _kind, condition, then_node, else_node = node
    condition_value = eval_formula("=" + str(condition), ctx, state)
    branch = then_node if bool(condition_value) else else_node
    return _eval_if_node(branch, ctx, state)


def _eval_nested_if_formula(text: str, ctx: RecipeContext, state: RuntimeState) -> Any:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    node, consumed = _parse_if_node(lines, 0)
    if consumed != len(lines):
        raise NonRecipeError(f"nested if formula has trailing lines: {lines[consumed:]}")
    return _eval_if_node(node, ctx, state)


class _Runtime74627281(RawWorkatoRuntime):
    def _resolve_update_value(self, raw_value: Any, state: RuntimeState) -> Any:
        if isinstance(raw_value, str) and raw_value.startswith("="):
            text = raw_value[1:].strip()
            if text.startswith("if ") and "\n" in text:
                return _eval_nested_if_formula(text, self.ctx, state)
            date_ternary = _DATE_TERNARY_RE.fullmatch(text)
            if date_ternary:
                pill = date_ternary.group("pill")
                value = resolve_dp_json(pill, self.ctx, state)
                if not present(None if value is MISSING else value):
                    return "NULL"
                rendered = eval_formula(
                    "=_dp('" + pill + "').in_time_zone(\"Etc/UTC\")"
                    ".strftime(\"%Y-%m-%d %H:%M:%S.%L\")",
                    self.ctx,
                    state,
                )
                return "'" + str(rendered) + "'"
        return resolve_value(raw_value, self.ctx, state)

    def workato_variable_update(
        self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        raw_name = str(raw_input.get("name") or "")
        target_lines = [line.strip() for line in raw_name.splitlines() if line.strip()]
        if len(target_lines) <= 1:
            return super().workato_variable_update(node, _ctx, state)
        target_steps: set[str] = set()
        target_fields: list[str] = []
        for entry in target_lines:
            parts = entry.split(":")
            if len(parts) != 3:
                raise NonRecipeError(f"invalid multi-variable target line: {entry}")
            target_steps.add(parts[1])
            target_fields.append(parts[2])
        if len(target_steps) != 1:
            raise NonRecipeError(
                f"multi-variable update targets multiple steps: {sorted(target_steps)}"
            )
        resolved: dict[str, Any] = {}
        for key, raw_value in raw_input.items():
            if key == "name":
                continue
            value = self._resolve_update_value(raw_value, state)
            resolved[str(key)] = None if value is MISSING else value
        updates = {field: resolved[field] for field in target_fields if field in resolved}
        if not updates:
            raise NonRecipeError("multi-variable update resolved no field updates")
        target_step = next(iter(target_steps))
        target = state.steps.setdefault(target_step, {})
        if not isinstance(target, dict):
            raise RawRecipeExecutionError(f"variable target step is not an object: {target_step}")
        provider_target = state.data.setdefault("workato_variable", {}).setdefault(target_step, target)
        if not isinstance(provider_target, dict):
            raise RawRecipeExecutionError(f"variable provider target is not an object: {target_step}")
        target.update(updates)
        provider_target.update(updates)
        args = {"name": raw_name}
        args.update(resolved)
        return "workato_runtime.update_variables", args, dict(updates)


def validate_74627281(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    show_sql = str((actions[0].get("input") or {}).get("sql") or "")
    if show_sql != f"SHOW COLUMNS IN {LOG_TABLE}":
        raise RuntimeError(f"recipe {RECIPE_ID} SHOW COLUMNS mapping changed")
    max_sql = str((actions[1].get("input") or {}).get("sql") or "")
    for fragment in ("MAX(RIGHT(RECORD_ID", f"FROM {LOG_TABLE}"):
        if fragment not in max_sql:
            raise RuntimeError(f"recipe {RECIPE_ID} MAX record id SQL mapping changed")
    insert_sql = str((actions[8].get("input") or {}).get("sql") or "")
    for fragment in (
        f"INSERT INTO {LOG_TABLE}",
        "WHERE RECORD_ID NOT IN",
        "QUALIFY ROW_NUMBER() OVER (",
        "ORDER BY MODIFIED_AT DESC",
    ):
        if fragment not in insert_sql:
            raise RuntimeError(f"recipe {RECIPE_ID} INSERT SQL mapping changed")
    update_input = actions[4].get("input") if isinstance(actions[4].get("input"), dict) else {}
    if "\n" not in str(update_input.get("name") or "") or "69ccf40d" not in str(update_input.get("name") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} update_variables target mapping changed")
    new_record_formula = str(update_input.get("new_record_id") or "")
    if not new_record_formula.startswith("=if ") or "split(\"R\")" not in new_record_formula:
        raise RuntimeError(f"recipe {RECIPE_ID} new record id formula changed")
    catch_node = _find_catch(raw)
    if not isinstance(catch_node, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} try/catch mapping changed")
    catch_filter = catch_node.get("filter") if isinstance(catch_node.get("filter"), dict) else {}
    catch_rhs = {
        str(condition.get("rhs") or "")
        for condition in catch_filter.get("conditions") or []
        if isinstance(condition, dict)
    }
    if catch_rhs != set(CATCH_FILTER_FRAGMENTS):
        raise RuntimeError(f"recipe {RECIPE_ID} catch filter mapping changed")
    if str((catch_node.get("input") or {}).get("max_retry_count") or "") != "3":
        raise RuntimeError(f"recipe {RECIPE_ID} catch retry mapping changed")
    stop_reasons = _collect_stop_reasons(raw)
    if "Rows insertion failed" not in stop_reasons:
        raise RuntimeError(f"recipe {RECIPE_ID} mismatch stop mapping changed")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": _action_summary(actions),
    }


def seed_74627281(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_74627281(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    rows = parameters.get("rows") if isinstance(parameters, dict) else None
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger input requires a non-empty parameters.rows object list"
        )
    if str(data.get("now") or "").strip() == "":
        raise RuntimeError(
            f"recipe {RECIPE_ID} uses `now` for CREATED_AT/MODIFIED_AT; the variant must pin 'now'"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    snowflake_seed = seed_in.get("snowflake_live")
    tables = snowflake_seed.get("tables") if isinstance(snowflake_seed, dict) else None
    if not isinstance(tables, dict) or LOG_TABLE not in tables:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must define snowflake_live.tables[{LOG_TABLE!r}]"
        )
    table_spec = tables.get(LOG_TABLE) or {}
    declared_columns = table_spec.get("columns") if isinstance(table_spec, dict) else None
    if not isinstance(declared_columns, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed must declare explicit {LOG_TABLE} columns")
    # Canonical JSON serialization sorts object keys, so the ``columns`` map
    # cannot carry Snowflake's physical ordinal order for generated variants.
    # Accept an explicit order sidecar (the same convention used by the
    # simulator) and retain map insertion order as a legacy fallback.
    order_sidecar = snowflake_seed.get("table_column_order")
    explicit_order = (
        order_sidecar.get(LOG_TABLE)
        if isinstance(order_sidecar, dict)
        else None
    )
    declared_order = tuple(
        str(name).upper()
        for name in (
            explicit_order
            if isinstance(explicit_order, list)
            else declared_columns
        )
    )
    if declared_order != LOG_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed column order must match the physical table order "
            f"(SHOW COLUMNS drives the INSERT): expected {LOG_COLUMNS}, got {declared_order}"
        )
    # The public/live seed sidecar is named ``table_column_order`` while the
    # simulated Snowflake adapter consumes its explicitly private transport
    # key. Translate at the harness boundary so SHOW COLUMNS observes the
    # declared physical order; do not rely on JSON object insertion order.
    provision_data = deepcopy(data)
    provision_snowflake = provision_data["seed"]["snowflake_live"]
    provision_snowflake["_simulated_column_order"] = {
        LOG_TABLE: list(LOG_COLUMNS)
    }
    provision = seed_live_snowflake(RECIPE_ID, provision_data, ctx)
    snowflake_state = deepcopy(provision["state"])
    snowflake_state["table_column_order"] = {LOG_TABLE: list(LOG_COLUMNS)}
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "now": data["now"],
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "snowflake_live": snowflake_state,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    simulated_insert = data.get("simulated_insert_result")
    if simulated_insert is not None:
        if not isinstance(simulated_insert, dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} simulated_insert_result must be an object"
            )
        sql = str(simulated_insert.get("sql") or "")
        rows_affected = simulated_insert.get("rows_affected")
        if (
            not sql.startswith(f"INSERT INTO {LOG_TABLE}\n")
            or not isinstance(rows_affected, int)
            or isinstance(rows_affected, bool)
            or rows_affected < 0
            or rows_affected > len(rows)
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} simulated_insert_result must bind the exact "
                "subscription-log INSERT and a feasible rows_affected count"
            )
        # Exact hidden connector-result fixture: this models a successful
        # partial write report without publishing simulator syntax to the
        # planner.  Argument matching remains fail-closed on the full SQL.
        out["_simulated_read_fixtures"] = [
            {
                "tool": "snowflake.run_custom_sql",
                "args": {"sql": sql, "parameters": {}},
                "result": {
                    "ok": True,
                    "rows": [],
                    "records": [],
                    "count": 0,
                    "rows_affected": rows_affected,
                },
            }
        ]
    return attach_variant(out, ctx)


def run_74627281(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_74627281(raw)
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        raw_execution = _Runtime74627281(ctx, seed).execute(raw)
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
    result["verifier"] = verify_74627281(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _find_catch(node: dict[str, Any]) -> dict[str, Any] | None:
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "catch":
            return child
        found = _find_catch(child)
        if found is not None:
            return found
    return None


def _collect_stop_reasons(node: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if node.get("keyword") == "stop":
        reasons.append(str((node.get("input") or {}).get("stop_reason") or ""))
    for child in node.get("block") or []:
        if isinstance(child, dict):
            reasons.extend(_collect_stop_reasons(child))
    return reasons


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
