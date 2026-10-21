from __future__ import annotations

import base64
import binascii
import datetime
import csv
import io
import json
import re
import sqlite3
import unicodedata
import urllib.parse
import zoneinfo
from copy import deepcopy
from dataclasses import dataclass, field
from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_HALF_UP,
)
from typing import Any, Callable

from .context import RecipeContext


class RawRecipeExecutionError(RuntimeError):
    pass


SKIP = object()
MISSING = object()


def epoch_seconds_in_timezone(seconds: Any, timezone_name: Any) -> str:
    """Render epoch seconds in an IANA timezone without a connector dependency."""

    try:
        value = float(str(seconds or "0"))
    except ValueError as exc:
        raise RuntimeError(f"invalid epoch seconds: {seconds}") from exc
    tz_name = str(timezone_name or "UTC")
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except zoneinfo.ZoneInfoNotFoundError as exc:
        raise RuntimeError(f"invalid timezone: {tz_name}") from exc
    return datetime.datetime.fromtimestamp(
        value, datetime.timezone.utc
    ).astimezone(tz).isoformat()


def ruby_to_s(value: Any) -> str:
    """Workato/Ruby render parity for pill/formula values in STRING contexts
    (template interpolation, bare-pill text mapping, SQL/SOQL slots, `.to_s`).
    Normative matrix (Ruby core to_s semantics; corpus live evidence, e.g.
    131596457 v06's unbound-nil SOQL slot rendering ''):
    Ruby: nil.to_s == "", false.to_s == "false", true.to_s == "true",
    0.to_s == "0", Array#to_s/Hash#to_s == inspect."""
    if value is MISSING or value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return value
    if isinstance(value, (list, dict)):
        return ruby_inspect(value)
    return str(value)


def ruby_inspect(value: Any) -> str:
    """Ruby #inspect — the form Array#to_s/Hash#to_s render inside string
    contexts (["a", "b"], {"k"=>"v"}; pre-Ruby-3.4 `=>` without spaces)."""
    if value is MISSING or value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        body = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\t", "\\t")
            .replace("\r", "\\r")
        )
        return f'"{body}"'
    if isinstance(value, list):
        return "[" + ", ".join(ruby_inspect(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{ruby_inspect(key)}=>{ruby_inspect(item)}" for key, item in value.items()) + "}"
    return str(value)


def action_schema_value(node: dict[str, Any], field_name: str, value: Any) -> Any:
    """Apply Workato action-schema conversions to a resolved field value.

    Raw recipe exports commonly store checkbox selections as the strings
    ``"true"``/``"false"`` even though the action's extended input schema
    declares a boolean. The connector receives the schema-converted value, so
    the simulator must not expose the editor's serialized string as runtime
    behavior.
    """

    field_schema: dict[str, Any] | None = None
    for schema_key in ("extended_input_schema", "input_schema"):
        schema_rows = node.get(schema_key)
        if not isinstance(schema_rows, list):
            continue
        field_schema = next(
            (
                row
                for row in schema_rows
                if isinstance(row, dict) and str(row.get("name") or "") == field_name
            ),
            None,
        )
        if field_schema is not None:
            break
    if field_schema is None:
        return value

    def convert(candidate: Any, schema: dict[str, Any]) -> Any:
        schema_type = str(schema.get("type") or "")
        if schema_type == "boolean" and isinstance(candidate, str):
            normalized = candidate.strip().lower()
            if normalized == "true":
                return True
            if normalized == "false":
                return False
        properties = schema.get("properties")
        if isinstance(candidate, dict) and isinstance(properties, list):
            by_name = {
                str(row.get("name") or ""): row
                for row in properties
                if isinstance(row, dict) and row.get("name")
            }
            return {
                key: convert(child, by_name[key]) if key in by_name else child
                for key, child in candidate.items()
            }
        if isinstance(candidate, list):
            item_schema = schema.get("items")
            if isinstance(item_schema, dict):
                return [convert(child, item_schema) for child in candidate]
            if isinstance(properties, list):
                object_schema = {"type": "object", "properties": properties}
                return [convert(child, object_schema) for child in candidate]
        return candidate

    return convert(value, field_schema)


class NonRecipeError(Exception):
    """A harness gap or benchmark-authoring error. Never part of recipe behavior:
    recipe-level try/catch must NOT absorb it (execute_try re-raises it), so a
    missing capability or bad seed always fails the run instead of silently
    becoming the recipe's catch branch."""



@dataclass
class RuntimeState:
    trigger: dict[str, Any]
    trigger_as: str
    trigger_provider: str
    steps: dict[str, Any] = field(default_factory=dict)
    data: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Per-foreach-step iteration metadata (keyed by the foreach step id):
    # {"index": <0-based>, "seq_no": <1-based>, "size": <total>}. Exposed to
    # formulas via the `foreach_meta` source, e.g. _('data.foreach.<line>.index',
    # 'foreach_meta').
    foreach_meta: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Declare-step fields whose schema carries integer_conversion, keyed by
    # the declare step id; update_variables coerces writes to these fields so
    # counter accumulation stays arithmetic across iterations.
    integer_variable_fields: dict[str, set[str]] = field(default_factory=dict)
    # Next index into seed.workato_uuids for =workato.uuid (deterministic,
    # consumed in call order).
    workato_uuid_index: int = 0
    trace: list[dict[str, Any]] = field(default_factory=list)
    # Control decisions are recorded separately from connector/action trace
    # rows so existing action-count and tool-sequence verification remains
    # stable while coverage consumers can distinguish an unexecuted branch
    # from an executed empty branch.
    control_trace: list[dict[str, Any]] = field(default_factory=list)
    last_error: Exception | None = None
    last_failed_action: dict[str, Any] | None = None
    return_value: Any = None
    stopped: bool = False

    def __post_init__(self) -> None:
        self.steps[self.trigger_as] = self.trigger
        self.data.setdefault(self.trigger_provider, {})[self.trigger_as] = self.trigger

    def record_step(self, node: dict[str, Any], tool: str, args: dict[str, Any], result: dict[str, Any]) -> None:
        step_id = step_key(node, len(self.trace))
        self.steps[step_id] = result
        provider = str(node.get("provider") or "")
        if provider:
            self.data.setdefault(provider, {})[step_id] = result
        self.trace.append(trace_base(node) | {"tool": tool, "args": deepcopy(args), "result": deepcopy(result)})


ActionAdapter = Callable[[dict[str, Any], RecipeContext, RuntimeState], tuple[str, dict[str, Any], dict[str, Any]]]


class RawWorkatoRuntime:
    def __init__(self, ctx: RecipeContext, seed: dict[str, Any]) -> None:
        self.ctx = ctx
        self.seed = seed
        self.adapters: dict[tuple[str, str], ActionAdapter] = {
            ("slack_bot", "post_bot_reply_v2"): self.slack_bot_reply,
            ("slack_bot", "post_bot_message"): self.slack_post_message,
            ("slack_bot", "get_user_by_email"): self.slack_bot_get_user_by_email,
            ("slack_bot", "open_bot_app_home"): self.slack_bot_open_bot_app_home,
            ("slack_bot", "block_kit_modals"): self.slack_bot_block_kit_modals,
            ("slack_bot", "generate_menu_options"): self.slack_generate_menu_options,
            ("slack_bot", "update_blocks_by_block_id"): self.slack_update_blocks_by_block_id,
            ("slack", "get_user_by_email"): self.slack_bot_get_user_by_email,
            ("slack", "post_message_to_channel"): self.slack_post_message,
            ("workato_db_table", "get_records"): self.workato_db_table_get,
            ("workato_db_table", "add_record"): self.workato_db_table_add,
            ("workato_db_table", "update_record"): self.workato_db_table_update,
            ("workato_db_table", "upsert_record"): self.workato_db_table_upsert,
            ("lookup_table", "get_entries"): self.lookup_table_get_entries,
            ("lookup_table", "get_entry"): self.lookup_table_get_entry,
            ("lookup_table", "search_entries"): self.lookup_table_search,
            ("lookup_table", "add_entry"): self.lookup_table_add,
            ("lookup_table", "update_entry"): self.lookup_table_update,
            ("lookup_table", "delete_entry"): self.lookup_table_delete,
            ("lookup_table", "truncate"): self.lookup_table_truncate,
            ("lookup_table", "add_batch_of_entries"): self.lookup_table_add_batch,
            ("json_parser", "parse_json"): self.json_parser_parse_json,
            ("google_sheets", "add_spreadsheet_row_v4"): self.google_sheets_add_row,
            ("google_sheets", "add_row_v4_bulk"): self.google_sheets_add_rows_bulk,
            ("google_sheets", "get_spreadsheet_rows_v4"): self.google_sheets_get_rows,
            ("google_sheets", "search_spreadsheet_rows_v4_new"): self.google_sheets_search_rows,
            ("google_sheets", "update_row_v4_new"): self.google_sheets_update_row,
            ("google_drive", "create_folder"): self.google_drive_create_folder,
            ("clock", "wait_for_interval"): self.clock_wait_for_interval,
            ("workato_db_table", "delete_record"): self.workato_db_table_delete,
            ("salesforce", "search_sobjects_soql_bulk_csv_v2"): self.salesforce_bulk_csv,
            ("snowflake", "upsert_rows_batch"): self.snowflake_upsert_rows_batch,
            ("snowflake", "update_rows"): self.snowflake_update_rows,
            ("snowflake", "search_rows"): self.snowflake_search_rows,
            ("snowflake", "search_rows_sql"): self.snowflake_search_rows_sql,
            ("snowflake", "run_custom_sql"): self.snowflake_run_custom_sql,
            ("workato_smart_list", "create_list_from_csv"): self.workato_smart_list_create_from_csv,
            ("workato_smart_list", "create_list"): self.workato_smart_list_create_list,
            ("workato_smart_list", "query_list"): self.workato_smart_list_query,
            ("workato_variable", "declare_variable"): self.workato_variable_declare_variable,
            ("workato_variable", "declare_list"): self.workato_variable_declare_list,
            ("workato_variable", "update_variables"): self.workato_variable_update,
            ("workato_variable", "update_variable"): self.workato_variable_update_single,
            ("workato_variable", "insert_to_list"): self.workato_variable_insert_to_list,
            ("workato_list", "create_list"): self.workato_list_create_list,
            ("workato_list", "accumulate_list_items"): self.workato_list_accumulate_list_items,
            ("workato_variable", "insert_to_list_batch"): self.workato_variable_insert_to_list_batch,
            ("workato_recipe_function", "return_result"): self.workato_return_result,
            ("workato_api_platform", "return_response"): self.workato_api_return_response,
            ("workato_service", "send_reply"): self.workato_service_send_reply,
            ("workato_service", "call_service"): self.workato_service_call_service,
            ("workato_service", "call_service_async"): self.workato_service_call_service_async,
            ("workato_app", "start_recipe"): self.workato_app_start_recipe,
            ("workato_app", "stop_recipe"): self.workato_app_stop_recipe,
            ("workato_app", "rerun_jobs"): self.workato_app_rerun_jobs,
            ("workato_app", "list_jobs"): self.workato_app_list_jobs,
            ("workato_app", "get_recipe"): self.workato_app_get_recipe,
            ("workato_db_table", "truncate_table"): self.workato_db_table_truncate_table,
            ("workato_pub_sub", "publish_to_topic"): self.workato_pub_sub_publish_to_topic,
            ("workato_pub_sub", "publish_to_topic_batch"): self.workato_pub_sub_publish_to_topic_batch,
            ("workato_genie", "workflow_return_result"): self.workato_genie_return_result,
            ("salesforce", "search_sobjects_soql_v2"): self.salesforce_search,
            ("salesforce", "search_sobjects_soql"): self.salesforce_search,
            ("salesforce", "search_sobjects"): self.salesforce_search,
            ("salesforce", "get_custom_object"): self.salesforce_get,
            ("salesforce", "update_sobject"): self.salesforce_update,
            ("salesforce", "composite_update_sobject"): self.salesforce_update,
            ("salesforce", "upsert_sobject"): self.salesforce_upsert,
            ("salesforce", "create_custom_object"): self.salesforce_create,
            ("salesforce", "create_sobject"): self.salesforce_create,
            ("jira", "create_issue"): self.jira_create_issue,
            ("logger", "log_message"): self.logger_log_message,
        }
        self.smart_lists: dict[str, list[dict[str, Any]]] = {}
        # Column order per smart-list table, tracked for CREATE TABLE / INSERT
        # INTO ... VALUES positional inserts (workato_smart_list.query_list).
        self.smart_list_columns: dict[str, list[str]] = {}

    def execute(self, raw: dict[str, Any]) -> dict[str, Any]:
        if raw.get("keyword") != "trigger":
            raise RawRecipeExecutionError("raw recipe root is not a trigger")
        state = RuntimeState(
            trigger=trigger_output(self.seed),
            trigger_as=str(raw.get("as") or "trigger"),
            trigger_provider=str(raw.get("provider") or "trigger"),
        )
        # Expose the seeded job_context so underscore data-calls
        # (_('data.workato.job_context.<field>')) resolve the same seed section
        # that the _dp job_context pill type reads. Additive: only present when
        # the recipe seeds job_context.
        if isinstance(self.seed.get("job_context"), dict):
            state.data.setdefault("workato", {})["job_context"] = self.seed["job_context"]
        trigger_filter_matched = True
        if isinstance(raw.get("filter"), dict):
            trigger_filter_matched = self.condition(raw["filter"], state)
        if trigger_filter_matched:
            self.execute_nodes(raw.get("block") or [], state)
        return {
            "trigger": state.trigger,
            "trigger_filter_matched": trigger_filter_matched,
            "raw_action_count": count_actions(raw.get("block") or []),
            "executed_action_count": sum(
                1 for row in state.trace if row.get("keyword") == "action" and row.get("tool")
            ),
            "trace": state.trace,
            "control_trace": state.control_trace,
            "step_outputs": state.steps,
            "data": state.data,
            "return_value": state.return_value,
        }

    def execute_nodes(self, nodes: list[Any], state: RuntimeState) -> None:
        idx = 0
        while idx < len(nodes) and not state.stopped:
            node = nodes[idx]
            if not isinstance(node, dict):
                raise RawRecipeExecutionError("raw block contains a non-object node")
            if node.get("keyword") in {"else", "catch"}:
                idx += 1
                continue
            self.execute_node(node, state)
            idx += 1

    def execute_node(self, node: dict[str, Any], state: RuntimeState) -> None:
        if node.get("skip"):
            state.trace.append(trace_base(node) | {"skipped": True})
            return
        keyword = node.get("keyword")
        if keyword == "action":
            tool, args, result = self.execute_action(node, state)
            state.record_step(node, tool, args, result)
            if tool in TERMINAL_TOOLS:
                state.stopped = True
            return
        if keyword == "if":
            self.execute_if(node, state)
            return
        if keyword == "foreach":
            self.execute_foreach(node, state)
            return
        if keyword == "try":
            self.execute_try(node, state)
            return
        if keyword == "repeat":
            self.execute_repeat(node, state)
            return
        if keyword == "stop":
            raw_input = node.get("input") if isinstance(node.get("input"), dict) else {}
            stop_reason = resolve_text(raw_input.get("stop_reason"), self.ctx, state)
            stop_with_error = truthy(
                resolve_value(raw_input.get("stop_with_error"), self.ctx, state)
            )
            state.stopped = True
            state.trace.append(
                trace_base(node)
                | {
                    "stopped": True,
                    "stop_reason": stop_reason,
                    "stop_with_error": stop_with_error,
                }
            )
            return
        raise RawRecipeExecutionError(
            "unsupported raw block keyword %r at step %r" % (keyword, node.get("number"))
        )

    def execute_repeat(self, node: dict[str, Any], state: RuntimeState) -> None:
        # Workato repeat/while pagination loop (do-while): execute the block
        # body, then evaluate the trailing while_condition node's compound
        # condition; continue while true. Iteration-capped for safety.
        children = [child for child in node.get("block") or [] if isinstance(child, dict)]
        body = [child for child in children if child.get("keyword") != "while_condition"]
        while_node = next(
            (child for child in children if child.get("keyword") == "while_condition"),
            None,
        )
        for _ in range(100):
            self.execute_nodes(body, state)
            if state.stopped:
                return
            if while_node is None:
                return
            if not self.condition(while_node.get("input") or {}, state):
                return
        raise RawRecipeExecutionError(
            "repeat loop exceeded 100 iterations at step %r" % node.get("number")
        )

    def execute_if(self, node: dict[str, Any], state: RuntimeState) -> None:
        children = [child for child in node.get("block") or [] if isinstance(child, dict)]
        branch_nodes = [
            child for child in children if child.get("keyword") not in {"elsif", "else"}
        ]
        if self.condition(node.get("input") or {}, state):
            state.control_trace.append(
                trace_base(node)
                | {"control_type": "if", "branch": "condition_true"}
            )
            self.execute_nodes(branch_nodes, state)
            return
        state.control_trace.append(
            trace_base(node)
            | {"control_type": "if", "branch": "condition_false"}
        )
        for child in children:
            if child.get("keyword") == "elsif":
                selected = self.condition(child.get("input") or {}, state)
                state.control_trace.append(
                    trace_base(child)
                    | {
                        "control_type": "if",
                        "branch": (
                            "condition_true" if selected else "condition_false"
                        ),
                    }
                )
                if selected:
                    self.execute_nodes(child.get("block") or [], state)
                    return
            if child.get("keyword") == "else":
                self.execute_nodes(child.get("block") or [], state)
                return

    def execute_foreach(self, node: dict[str, Any], state: RuntimeState) -> None:
        raw_input = input_obj(node)
        source = resolve_value(raw_input.get("source"), self.ctx, state)
        if source is MISSING:
            raise RawRecipeExecutionError(f"foreach source missing at step {node.get('number')}")
        step_id = step_key(node, len(state.trace))
        if node.get("repeat_mode") == "batch":
            batch = as_list(source)
            state.steps[step_id] = {"batch": batch}
            state.data.setdefault("foreach", {})[step_id] = {"batch": batch}
            state.foreach_meta[step_id] = {"size": len(batch)}
            if batch:
                # Workato batch loops run zero iterations on an empty source.
                self.execute_nodes(node.get("block") or [], state)
            return
        items = as_list(source)
        total = len(items)
        # Record size before iterating so a zero-iteration loop still reports
        # size 0 to later foreach_meta reads.
        state.foreach_meta[step_id] = {"size": total}
        for index, item in enumerate(items):
            state.steps[step_id] = item
            state.data.setdefault("foreach", {})[step_id] = item
            state.foreach_meta[step_id] = {"index": index, "seq_no": index + 1, "size": total}
            self.execute_nodes(node.get("block") or [], state)

    def execute_try(self, node: dict[str, Any], state: RuntimeState) -> None:
        children = node.get("block") or []
        body = [child for child in children if not (isinstance(child, dict) and child.get("keyword") == "catch")]
        catch_node = next((child for child in children if isinstance(child, dict) and child.get("keyword") == "catch"), None)
        try:
            self.execute_nodes(body, state)
            state.control_trace.append(
                trace_base(node)
                | {"control_type": "try", "branch": "try_success"}
            )
        except NonRecipeError:
            raise
        except Exception as exc:
            state.last_error = exc
            if isinstance(catch_node, dict):
                state.control_trace.append(
                    trace_base(node)
                    | {"control_type": "try", "branch": "exception"}
                )
                catch_id = step_key(catch_node, len(state.trace))
                failed_action = state.last_failed_action or {}
                payload = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    # Workato catch datapills expose the connector adapter,
                    # action, and failing line.  These fields are necessary
                    # for recipes that distinguish a normal not-found error
                    # from unrelated connector failures.
                    "adapter": str(failed_action.get("adapter") or ""),
                    "action": str(failed_action.get("action") or ""),
                    "line_number": failed_action.get("line_number"),
                }
                state.steps[catch_id] = payload
                state.data.setdefault("catch", {})[catch_id] = payload
                self.execute_nodes(catch_node.get("block") or [], state)
            else:
                raise

    def execute_action(self, node: dict[str, Any], state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        key = (str(node.get("provider") or ""), str(node.get("name") or ""))
        state.last_failed_action = None
        try:
            forced_error = self.forced_action_error(node)
            if forced_error:
                raise RawRecipeExecutionError(forced_error)
            adapter = self.adapters.get(key)
            if not adapter:
                raise NonRecipeError("unsupported raw action %s.%s" % key)
            return adapter(node, self.ctx, state)
        except Exception:
            state.last_failed_action = {
                "adapter": key[0],
                "action": key[1],
                "line_number": node.get("number"),
                "step_as": node.get("as"),
            }
            raise

    def forced_action_error(self, node: dict[str, Any]) -> str:
        force = self.seed.get("force_action_error")
        if not isinstance(force, dict):
            return ""
        step_as = force.get("step_as")
        step_number = force.get("step_number")
        matches_as = step_as not in (None, "") and str(node.get("as") or "") == str(step_as)
        matches_number = step_number not in (None, "") and str(node.get("number") or "") == str(step_number)
        if matches_as or matches_number:
            return str(force.get("error") or "benchmark forced raw action failure")
        return ""

    def condition(self, raw: dict[str, Any], state: RuntimeState) -> bool:
        if raw.get("type") == "compound":
            op = str(raw.get("operand") or "and").lower()
            conditions = [cond for cond in raw.get("conditions") or [] if isinstance(cond, dict)]
            # Short-circuit like Workato: a later condition that would error
            # (e.g. blank compare) never evaluates once the outcome is fixed.
            if op == "or":
                return any(self.condition(cond, state) for cond in conditions)
            return all(self.condition(cond, state) for cond in conditions)
        lhs = resolve_value(raw.get("lhs"), self.ctx, state)
        rhs = resolve_value(raw.get("rhs"), self.ctx, state)
        # Workato interpolation semantics: a nil/never-run pill in a condition
        # slot renders "" (then e.g. "" > '0' is a string compare → false),
        # never an execution error. None covers both a genuinely nil pill
        # value and a nil-PROPAGATED path walk (lookup_path): both are nil in
        # Workato and render "" here, exactly like the MISSING sentinel did
        # before nil propagation was distinguished from unknown sources.
        if lhs is MISSING or lhs is None:
            lhs = ""
        if rhs is MISSING or rhs is None:
            rhs = ""
        # Mixed anonymization — a tagged condition literal against a clean
        # seeded value (or vice versa) can never be INTENDED to differ; strip
        # the wrapped side so equality/negation semantics hold. Self-consistent
        # tagged pairs (both sides wrapped) stay verbatim.
        lhs_wrapped = isinstance(lhs, str) and lhs.startswith("<anon>") and lhs.endswith("</anon>")
        rhs_wrapped = isinstance(rhs, str) and rhs.startswith("<anon>") and rhs.endswith("</anon>")
        if lhs_wrapped != rhs_wrapped:
            if lhs_wrapped:
                lhs = strip_anon_wrapper(lhs)
            if rhs_wrapped:
                rhs = strip_anon_wrapper(rhs)
        operand = str(raw.get("operand") or "").lower()
        if operand == "contains":
            if isinstance(lhs, list):
                return any(str(item) == str(rhs) for item in lhs)
            return str(rhs) in str(lhs)
        if operand == "ends_with":
            return str(lhs).endswith(str(rhs))
        if operand == "not_ends_with":
            return not str(lhs).endswith(str(rhs))
        if operand == "starts_with":
            return str(lhs).startswith(str(rhs))
        if operand == "not_starts_with":
            return not str(lhs).startswith(str(rhs))
        if operand == "present":
            return present(lhs)
        if operand == "blank":
            return not present(lhs)
        if operand in {"not_blank", "not_blank?"}:
            return present(lhs)
        if operand == "not_contains":
            return str(rhs) not in str(lhs)
        if operand in {"is_true", "is_true?"}:
            return truthy(lhs)
        if operand in {"is_not_true", "is_not_true?"}:
            return not truthy(lhs)
        if operand in {"equals_to", "equals", "=="}:
            return str(lhs) == str(rhs)
        if operand in {"not_equals_to", "!="}:
            return str(lhs) != str(rhs)
        if operand == "greater_than":
            return compare_condition_values(lhs, rhs) > 0
        if operand == "less_than":
            return compare_condition_values(lhs, rhs) < 0
        raise NonRecipeError(f"unsupported condition operand: {operand}")

    def slack_bot_reply(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        trigger = state.trigger
        parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else {}
        message = self.seed.get("message") if isinstance(self.seed.get("message"), dict) else {}
        blocks = resolve_value(raw_input.get("blocks") or [], self.ctx, state)
        if not isinstance(blocks, list):
            raise RawRecipeExecutionError("Slack reply blocks must resolve to a list")
        args = {
            "channel": str(
                self.ctx.env.slack_channel_override
                or message.get("channel")
                or trigger.get("channel")
                or parameters.get("channel")
                or ""
            ),
            "thread_ts": str(trigger.get("message_ts") or trigger.get("ts") or parameters.get("message_ts") or parameters.get("ts") or ""),
            "text": slack_text(
                raw_input,
                self.ctx,
                state,
                allow_empty=truthy(raw_input.get("delete_original")),
            ),
            "blocks": blocks,
            "user": str(trigger.get("user") or parameters.get("user") or ""),
            "original_ts": str(
                message.get("ts")
                or trigger.get("message_ts")
                or trigger.get("ts")
                or parameters.get("message_ts")
                or parameters.get("ts")
                or ""
            ),
            "ephemeral": truthy(raw_input.get("ephemeral_message")),
            "replace_original": truthy(raw_input.get("replace_original")),
            "delete_original": truthy(raw_input.get("delete_original")),
        }
        return call_tool(self.ctx, "slack.post_reply", args)

    def slack_post_message(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        raw_channel = resolve_value(raw_input.get("channel"), self.ctx, state)
        raw_channel_text = str(raw_channel or "")
        # Opt-in seed mapping for raw recipes that hardcode literal user-id
        # channels that do not exist in the benchmark workspace. A variant's
        # seed may carry slack_channel_map: {"U069...": "__override__"} to
        # route such literals to the benchmark override channel (or another
        # explicit channel id). Resolved live user ids are unaffected unless
        # explicitly mapped.
        channel_map = self.seed.get("slack_channel_map") if isinstance(self.seed.get("slack_channel_map"), dict) else {}
        if raw_channel_text in channel_map:
            mapped = str(channel_map[raw_channel_text] or "")
            raw_channel_text = self.ctx.env.slack_channel_override if mapped == "__override__" else mapped
        channel = raw_channel_text if raw_channel_text.startswith("U") else self.ctx.env.slack_channel_override or raw_channel_text
        advanced = raw_input.get("advanced") if isinstance(raw_input.get("advanced"), dict) else {}
        text = slack_text(raw_input, self.ctx, state)
        args = {
            "channel": str(channel or ""),
            "text": text,
            "thread_ts": resolve_text(advanced.get("thread_ts"), self.ctx, state),
            "ts": resolve_text(advanced.get("ts"), self.ctx, state),
        }
        attachments = slack_attachments(raw_input, self.ctx, state)
        if attachments:
            args["attachments"] = attachments
        return call_tool(self.ctx, "slack.post_message", args)

    def slack_bot_get_user_by_email(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        email = resolve_value(raw_input.get("email"), self.ctx, state)
        user_id = resolve_value(raw_input.get("id"), self.ctx, state)
        args = {"email": str(email or "")} if email not in (None, "") else {"id": str(user_id or "")}
        return call_tool(self.ctx, "slack_bot.get_user_by_email", args)

    def slack_bot_open_bot_app_home(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            "user_id": resolve_text(raw_input.get("user_id"), self.ctx, state),
            "view": {"blocks": resolve_value(raw_input.get("blocks") or [], self.ctx, state)},
        }
        return call_tool(self.ctx, "slack_bot.open_bot_app_home", args)

    def slack_bot_block_kit_modals(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            "modal_action_type": resolve_text(raw_input.get("modal_action_type"), self.ctx, state),
            "trigger_id": resolve_text(raw_input.get("trigger_id"), self.ctx, state),
            "view": resolve_value(raw_input.get("view") or {}, self.ctx, state),
        }
        return call_tool(self.ctx, "slack_bot.block_kit_modals", args)

    def slack_generate_menu_options(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        raw_groups = raw_input.get("option_groups")
        if isinstance(raw_groups, list) and all(
            isinstance(group, dict) and not group for group in raw_groups
        ):
            # Vestigial editor placeholder (`"option_groups": [{}]` alongside
            # use_option_groups "false") — no bindable content; the real menu
            # source lives on the flat options.____source path below.
            raw_groups = None
        if raw_groups:
            # Workato group-expansion idiom: the group's `label` slot binds the
            # SOURCE list pill and the option templates use bare current_item
            # pills over it — one option per source row.
            groups_out: list[dict[str, Any]] = []
            flat: list[dict[str, Any]] = []
            for group in as_list(raw_groups):
                if not isinstance(group, dict):
                    raise RawRecipeExecutionError("slack_bot.generate_menu_options option group must be an object")
                source_raw = group.get("label")
                source_pill = source_raw
                if isinstance(source_raw, str) and source_raw.startswith("=_dp("):
                    source_pill = "#{" + source_raw[1:] + "}"
                info = source_datapill_info(source_pill)
                if not info:
                    raise RawRecipeExecutionError(
                        "slack_bot.generate_menu_options option group label must bind a source datapill"
                    )
                rows = as_list(resolve_value(source_raw, self.ctx, state))
                rendered: list[dict[str, Any]] = []
                for row in rows:
                    with_source_current_item(state, info, row)
                    try:
                        for template in group.get("options") or []:
                            resolved = resolve_value(template, self.ctx, state)
                            if not isinstance(resolved, dict):
                                raise RawRecipeExecutionError(
                                    "slack_bot.generate_menu_options option must resolve to an object"
                                )
                            rendered.append(resolved)
                    finally:
                        restore_source_current_item(state, info)
                groups_out.append({"options": rendered})
                flat.extend(rendered)
            return call_tool(
                self.ctx,
                "slack_bot.generate_menu_options",
                {"options": flat, "option_groups": groups_out},
            )
        options = resolve_value(raw_input.get("options") or [], self.ctx, state)
        if not isinstance(options, list):
            raise RawRecipeExecutionError("slack_bot.generate_menu_options options must resolve to a list")
        return call_tool(self.ctx, "slack_bot.generate_menu_options", {"options": options})

    def slack_update_blocks_by_block_id(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        blocks_to_update = resolve_value(raw_input.get("blocks_to_update") or [], self.ctx, state)
        if not isinstance(blocks_to_update, list):
            raise RawRecipeExecutionError("slack_bot.update_blocks_by_block_id blocks_to_update must resolve to a list")
        args = {
            "message_json": resolve_value(raw_input.get("message_json"), self.ctx, state),
            "blocks_to_update": blocks_to_update,
        }
        return call_tool(self.ctx, "slack.update_blocks_by_block_id", args)

    def jira_create_issue(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            "project_issuetype": resolve_text(raw_input.get("project_issuetype"), self.ctx, state),
            "summary": resolve_text(raw_input.get("summary"), self.ctx, state),
            "description": resolve_text(raw_input.get("description"), self.ctx, state),
            "priority": resolve_text(raw_input.get("priority"), self.ctx, state),
            "labels": resolve_value(raw_input.get("labels"), self.ctx, state),
        }
        return call_tool(self.ctx, "jira.create_issue", args)

    def workato_db_table_upsert(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        # Data-table write args are NOT nil-compacted (unlike the Salesforce
        # write handlers): a column MAPPED to a pill that resolves nil is sent
        # as null in the request; only columns absent from the recipe mapping
        # or mapped to `=skip` are omitted (resolved_parameters drops SKIP).
        # Nil-compaction happens at the STORAGE boundary instead — the
        # data-table mock's _clean drops null params, so the previous stored
        # value survives an update/upsert (never overwritten by null). This
        # two-layer split is the corpus-pinned semantics (verify_86990074 /
        # verify_121086244 / verify_123216893 SEMANTIC TRAPS); judged
        # 2026-07-13: the mock's _clean is a storage-boundary rule, not a
        # request encoder, so requests faithfully carry mapped-nil as null.
        record = resolved_parameters(raw_input, self.ctx, state)
        primary = primary_field_id(raw_input.get("primary_field_id"), record, state, node)
        args = {
            "table_id": resolve_text(raw_input.get("table_id"), self.ctx, state),
            "primary_field_id": primary,
            "record": record,
        }
        return call_tool(self.ctx, "workato_db_table.upsert_record", args)

    def workato_db_table_get(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            "table_id": resolve_text(raw_input.get("table_id"), self.ctx, state),
            "filters": workato_db_filters(raw_input, self.ctx, state),
        }
        if "continuation_token" in raw_input:
            token = resolve_value(raw_input.get("continuation_token"), self.ctx, state)
            if token is SKIP:
                # `=cursor.presence || skip` on the first page: Workato omits
                # the parameter entirely (the SKIP sentinel must never reach
                # tool args or the trace).
                pass
            else:
                args["continuation_token"] = "" if token in (None, MISSING) else str(token)
        # Workato exports editor defaults (limit=100, direction=asc) even when
        # no ordering/cap was intentionally configured.  Omit that inert pair,
        # but preserve every meaningful modifier deterministically.  Hidden
        # fixture flags must never change the public connector call shape.
        configured_limit = raw_input.get("limit")
        has_nondefault_limit = configured_limit not in (None, "", "100", 100)
        has_order = raw_input.get("order_by_field_id") not in (None, "")
        if has_nondefault_limit or has_order:
            for key in ("order_by_field_id", "order_direction", "limit"):
                if key in raw_input:
                    value = resolve_value(raw_input.get(key), self.ctx, state)
                    if value is not SKIP and value not in (None, MISSING, ""):
                        # The public connector contract declares limit as an
                        # integer even though Workato exports the editor value
                        # as a string. Preserve strings for ordering metadata,
                        # but expose the connector-received numeric cap.
                        args[key] = int(value) if key == "limit" else str(value)
            if "order_by_field_id" in args:
                # Mock rows key by underscored field ids; a dashed order key
                # would silently sort on all-equal misses.
                args["order_by_field_id"] = normalize_workato_field_id(args["order_by_field_id"])
        return call_tool(self.ctx, "workato_db_table.get_records", args)

    def workato_db_table_add(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            "table_id": resolve_text(raw_input.get("table_id"), self.ctx, state),
            # No nil-compaction: mapped-nil columns stay null in the args
            # (see workato_db_table_upsert for the request/storage two-layer
            # split).
            "record": resolved_parameters(raw_input, self.ctx, state),
            "record_id_field": resolve_value(raw_input.get("record_id_field"), self.ctx, state),
        }
        return call_tool(self.ctx, "workato_db_table.add_record", args)

    def workato_db_table_update(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        # No nil-compaction: mapped-nil columns stay null in the args; the
        # mock's storage _clean drops them so the previous cell value is kept
        # (see workato_db_table_upsert for the request/storage two-layer
        # split).
        record = resolved_parameters(raw_input, self.ctx, state)
        args = {
            "table_id": resolve_text(raw_input.get("table_id"), self.ctx, state),
            "record_id": resolve_value(raw_input.get("record_id"), self.ctx, state),
            "record_id_field": resolve_value(raw_input.get("record_id_field"), self.ctx, state),
            "record": record,
        }
        if args["record_id"] in (None, "", MISSING):
            args["record_id"] = raw_input.get("id")
        return call_tool(self.ctx, "workato_db_table.update_record", args)

    def workato_db_table_delete(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            "table_id": resolve_text(raw_input.get("table_id"), self.ctx, state),
            "record_id": resolve_value(raw_input.get("record_id") or raw_input.get("id"), self.ctx, state),
        }
        return call_tool(self.ctx, "workato_db_table.delete_record", args)

    def lookup_table_get_entries(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {"lookup_table_id": resolve_text(raw_input.get("lookup_table_id"), self.ctx, state)}
        return call_tool(self.ctx, "lookup_table.get_entries", args)

    def lookup_table_get_entry(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            "lookup_table_id": resolve_text(raw_input.get("lookup_table_id"), self.ctx, state),
            "id": resolve_value(raw_input.get("id"), self.ctx, state),
            "parameters": resolved_parameters(raw_input, self.ctx, state),
        }
        return call_tool(self.ctx, "lookup_table.get_entry", args)

    def lookup_table_search(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            "lookup_table_id": resolve_text(raw_input.get("lookup_table_id"), self.ctx, state),
            "parameters": resolved_parameters(raw_input, self.ctx, state),
        }
        return call_tool(self.ctx, "lookup_table.search_entries", args)

    def lookup_table_add(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            "lookup_table_id": resolve_text(raw_input.get("lookup_table_id"), self.ctx, state),
            "parameters": resolved_parameters(raw_input, self.ctx, state),
        }
        return call_tool(self.ctx, "lookup_table.add_entry", args)

    def lookup_table_truncate(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            "lookup_table_id": resolve_text(raw_input.get("lookup_table_id"), self.ctx, state),
        }
        return call_tool(self.ctx, "lookup_table.truncate", args)

    def lookup_table_add_batch(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        resolved_entries = resolve_value(raw_input.get("entries"), self.ctx, state)
        entries: list[dict[str, Any]] = []
        for item in as_list(resolved_entries):
            if not isinstance(item, dict):
                continue
            # ____source templates nest the row fields under "parameters".
            params = item.get("parameters") if isinstance(item.get("parameters"), dict) else item
            entries.append(params)
        args = {
            "lookup_table_id": resolve_text(raw_input.get("lookup_table_id"), self.ctx, state),
            "entries": entries,
        }
        return call_tool(self.ctx, "lookup_table.add_batch_of_entries", args)

    def lookup_table_update(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            "lookup_table_id": resolve_text(raw_input.get("lookup_table_id"), self.ctx, state),
            "id": resolve_value(raw_input.get("id"), self.ctx, state),
            "ignore_not_found": resolve_value(raw_input.get("ignore_not_found"), self.ctx, state),
            "parameters": resolved_parameters(raw_input, self.ctx, state),
        }
        if args["id"] in (None, "", MISSING):
            raise NonRecipeError("lookup_table.update_entry requires a resolved entry id")
        return call_tool(self.ctx, "lookup_table.update_entry", args)

    def lookup_table_delete(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            "lookup_table_id": resolve_text(raw_input.get("lookup_table_id"), self.ctx, state),
            "id": resolve_value(raw_input.get("id"), self.ctx, state),
            "ignore_not_found": resolve_value(raw_input.get("ignore_not_found"), self.ctx, state),
        }
        if args["id"] in (None, "", MISSING):
            raise NonRecipeError("lookup_table.delete_entry requires a resolved entry id")
        return call_tool(self.ctx, "lookup_table.delete_entry", args)

    def json_parser_parse_json(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        document = resolve_value(raw_input.get("document"), self.ctx, state)
        if document in (None, "", MISSING):
            raise RawRecipeExecutionError("json_parser received an empty document")
        if isinstance(document, str):
            try:
                parsed = json.loads(document)
            except json.JSONDecodeError as exc:
                raise RawRecipeExecutionError(f"json_parser.parse_json received invalid JSON at step {node.get('number')}") from exc
        else:
            parsed = document
        if isinstance(parsed, list) and _schema_wraps_array(node):
            # Workato exposes a top-level-array document under document.array
            # (the node's output schema declares document as {array: [...]}).
            parsed = {"array": parsed}
        args = {"document": document}
        return "workato_runtime.parse_json", args, {"ok": True, "document": parsed}

    def google_sheets_update_row(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        raw_data = raw_input.get("data") or {}
        resolved_data = resolve_value(raw_data, self.ctx, state)
        if not isinstance(resolved_data, dict):
            raise RawRecipeExecutionError(f"Google Sheets update row data must be an object at step {node.get('number')}")
        column_labels = _sheet_column_labels(node)
        data: dict[str, Any] = {}
        for key, value in resolved_data.items():
            header = column_labels.get(str(key), str(key))
            if header.startswith("col_"):
                header = header[4:]
            data[header] = value
        args = {
            "spreadsheet": resolve_value(raw_input.get("spreadsheet_id") or raw_input.get("spreadsheet"), self.ctx, state),
            "sheet": resolve_value(raw_input.get("sheet_name") or raw_input.get("sheet"), self.ctx, state),
            "row_number": resolve_value(raw_input.get("row_number"), self.ctx, state),
            "data": data,
        }
        return call_tool(self.ctx, "google_sheets.update_row_v4_new", args)

    def google_sheets_add_row(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        headers = _sheet_headers(resolve_value(raw_input.get("column_headers"), self.ctx, state))
        raw_columns = raw_input.get("columns") or raw_input.get("data") or {}
        column_labels = _sheet_column_labels(node)
        resolved_columns = resolve_value(raw_columns, self.ctx, state)
        if not isinstance(resolved_columns, dict):
            raise RawRecipeExecutionError(f"Google Sheets add row columns must be an object at step {node.get('number')}")
        data: dict[str, Any] = {}
        for key, value in resolved_columns.items():
            header = column_labels.get(str(key), str(key))
            if header.startswith("col_"):
                header = header[4:]
            data[header] = value
        if not headers and column_labels:
            headers = [label for key, label in column_labels.items() if key in resolved_columns]
        args = {
            "spreadsheet": resolve_value(raw_input.get("spreadsheet_id") or raw_input.get("spreadsheet"), self.ctx, state),
            "sheet": resolve_value(raw_input.get("sheet_name") or raw_input.get("sheet"), self.ctx, state),
            "headers": headers,
            "data": data,
        }
        return call_tool(self.ctx, "google_sheets.add_spreadsheet_row_v4", args)

    def google_sheets_add_rows_bulk(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        column_labels = _sheet_column_labels(node)
        resolved_rows = resolve_value(raw_input.get("rows") or [], self.ctx, state)
        if not isinstance(resolved_rows, list):
            raise RawRecipeExecutionError(f"Google Sheets bulk rows must resolve to a list at step {node.get('number')}")
        spreadsheet = resolve_value(raw_input.get("spreadsheet_id") or raw_input.get("spreadsheet"), self.ctx, state)
        sheet = resolve_value(raw_input.get("sheet_name") or raw_input.get("sheet"), self.ctx, state)
        headers = [label for label in column_labels.values()] if column_labels else []
        appended: list[dict[str, Any]] = []
        call_args: list[dict[str, Any]] = []
        for resolved_row in resolved_rows:
            if not isinstance(resolved_row, dict):
                raise RawRecipeExecutionError(f"Google Sheets bulk row item must be an object at step {node.get('number')}")
            data: dict[str, Any] = {}
            for key, value in resolved_row.items():
                header = column_labels.get(str(key), str(key))
                if header.startswith("col_"):
                    header = header[4:]
                data[header] = value
            args = {"spreadsheet": spreadsheet, "sheet": sheet, "headers": headers, "data": data}
            call_args.append(args)
            appended.append(self.ctx.tools.call("google_sheets.add_spreadsheet_row_v4", args))
        return (
            "google_sheets.add_spreadsheet_row_v4",
            {"spreadsheet": spreadsheet, "sheet": sheet, "headers": headers, "rows": [args["data"] for args in call_args]},
            {
                "ok": all(result.get("ok") for result in appended),
                "count": len(appended),
                "records": [record for result in appended for record in as_list(result.get("records"))],
                "results": appended,
            },
        )

    def google_sheets_get_rows(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            "spreadsheet": resolve_value(raw_input.get("spreadsheet_id") or raw_input.get("spreadsheet"), self.ctx, state),
            "sheet": resolve_value(raw_input.get("sheet_name") or raw_input.get("sheet"), self.ctx, state),
            "range": resolve_value(raw_input.get("range"), self.ctx, state),
        }
        return call_tool(self.ctx, "google_sheets.get_spreadsheet_rows_v4", args)

    def google_sheets_search_rows(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        count = resolve_value(raw_input.get("count"), self.ctx, state)
        args = {
            "spreadsheet": resolve_value(raw_input.get("spreadsheet_id") or raw_input.get("spreadsheet"), self.ctx, state),
            "sheet": resolve_value(raw_input.get("sheet_name") or raw_input.get("sheet"), self.ctx, state),
            "data": resolve_value(raw_input.get("data") or {}, self.ctx, state),
            "count": canonical_optional_integer(count),
        }
        tool, out_args, result = call_tool(self.ctx, "google_sheets.search_spreadsheet_rows_v4_new", args)
        # Live rows key by ACTUAL tab headers while pills deref the node
        # schema's col_<header> names; alias additively so label-headed tabs
        # round-trip. col_-literal tabs already carry the schema names, so
        # nothing changes for them.
        aliases = _sheets_schema_col_names(node)
        rows = result.get("rows")
        if aliases and isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                for alias in aliases:
                    header = alias[len("col_"):]
                    if alias not in row and header in row:
                        row[alias] = row[header]
        return tool, out_args, result

    def google_drive_create_folder(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            "parent_id": resolve_text(raw_input.get("folderId") or raw_input.get("parent_id"), self.ctx, state),
            "name": resolve_text(raw_input.get("name"), self.ctx, state),
        }
        return call_tool(self.ctx, "google_drive.create_folder", args)

    def clock_wait_for_interval(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {"interval": resolve_text(raw_input.get("interval"), self.ctx, state)}
        return call_tool(self.ctx, "clock.wait_for_interval", args)

    def salesforce_bulk_csv(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        query = resolve_text(raw_input.get("query"), self.ctx, state)
        if re.search(r"\bwhere\b", query, flags=re.I):
            raise NonRecipeError(
                "salesforce bulk CSV SOQL WHERE clauses are not translated; refusing to broaden the query"
            )
        sobject = salesforce_sobject(query)
        fields = salesforce_select_fields(query)
        if not fields:
            raise NonRecipeError(f"could not parse SELECT fields from bulk CSV SOQL: {query}")
        tool, args, search_result = call_tool(
            self.ctx,
            "salesforce.search_records",
            {
                "sobject": sobject,
                # Bulk SELECT without WHERE intentionally scans the selected
                # object.  The public search tool rejects an unconstrained
                # empty invocation, so express the same non-null Id domain
                # explicitly instead of weakening that safety contract.
                "query": "Id != null",
                "filters": [],
            },
        )
        rows = search_result.get("records") if isinstance(search_result.get("records"), list) else []
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        if truthy(raw_input.get("include_header")):
            writer.writerow(fields)
        for row in rows:
            if not isinstance(row, dict):
                continue
            writer.writerow([_record_field(row, field) for field in fields])
        result = {
            "ok": True,
            "results": output.getvalue().rstrip("\n"),
            "records": rows,
            "count": len(rows),
            "sobject": sobject,
            "fields": fields,
            "search_result": search_result,
        }
        # The model-facing catalog exposes the canonical search tool; the raw
        # Workato action name is provenance, not a second tool identity.
        return tool, args, result

    def snowflake_upsert_rows_batch(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        rows = resolve_value(raw_input.get("rows") or [], self.ctx, state)
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            raise RawRecipeExecutionError("snowflake.upsert_rows_batch rows must resolve to a list")
        args = {
            "table": resolve_text(raw_input.get("table"), self.ctx, state),
            "key_columns": resolve_value(raw_input.get("key_columns"), self.ctx, state)
            or snowflake_primary_key_columns(node),
            "rows": rows,
        }
        return call_tool(self.ctx, "snowflake.upsert_rows_batch", args)

    def snowflake_update_rows(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        columns = resolve_value(raw_input.get("columns") or {}, self.ctx, state)
        if not isinstance(columns, dict):
            raise RawRecipeExecutionError("snowflake.update_rows columns must resolve to an object")
        args = {
            "table": resolve_text(raw_input.get("table"), self.ctx, state),
            "where": resolve_text(raw_input.get("where"), self.ctx, state),
            "columns": columns,
        }
        return call_tool(self.ctx, "snowflake.update_rows", args)

    def snowflake_search_rows(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        resolved_limit = resolve_value(raw_input.get("limit"), self.ctx, state)
        resolved_offset = resolve_value(raw_input.get("offset"), self.ctx, state)
        args = {
            "table": resolve_text(raw_input.get("table"), self.ctx, state),
            "where": resolve_text(raw_input.get("where"), self.ctx, state),
            "parameters": snowflake_parameters(raw_input, self.ctx, state),
            "limit": canonical_optional_integer(resolved_limit),
            "offset": canonical_optional_integer(resolved_offset),
            "orderby": resolve_value(raw_input.get("orderby"), self.ctx, state),
            "output_columns": resolve_value(raw_input.get("output_columns"), self.ctx, state),
        }
        return call_tool(self.ctx, "snowflake.search_rows", args)

    def snowflake_search_rows_sql(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        sql = resolve_text(raw_input.get("sql"), self.ctx, state)
        orderby = resolve_text(raw_input.get("orderby"), self.ctx, state)
        if orderby and not _sql_has_top_level_order_by(sql):
            # The connector's separate Order-by input appends to the query.
            # ORDER BY inside parens (OVER(...) windows, subqueries) does not
            # order the outer statement and must not suppress the append.
            sql = f"{sql.rstrip().rstrip(';')} ORDER BY {orderby}"
        resolved_limit = resolve_value(raw_input.get("limit"), self.ctx, state)
        resolved_offset = resolve_value(raw_input.get("offset"), self.ctx, state)
        args = {
            "sql": sql,
            "parameters": snowflake_parameters(raw_input, self.ctx, state),
            "limit": canonical_optional_integer(resolved_limit),
            "offset": canonical_optional_integer(resolved_offset),
        }
        return call_tool(self.ctx, "snowflake.search_rows_sql", args)

    def snowflake_run_custom_sql(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            "sql": resolve_text(raw_input.get("sql"), self.ctx, state),
            "parameters": snowflake_parameters(raw_input, self.ctx, state),
        }
        return call_tool(self.ctx, "snowflake.run_custom_sql", args)

    def workato_smart_list_create_from_csv(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        list_name = resolve_text(raw_input.get("list_name"), self.ctx, state)
        csv_text = resolve_text(raw_input.get("list_source"), self.ctx, state)
        columns = smart_list_columns(raw_input.get("csv_schema_json"))
        if not columns:
            raise NonRecipeError("smart list create_from_csv requires a valid csv_schema_json column list")
        rows = smart_list_rows_from_csv(csv_text, columns, truthy(raw_input.get("headers")))
        self.smart_lists[_smart_list_key(list_name)] = rows
        result = {
            "ok": True,
            "list_name": list_name,
            "columns": {column: column for column in columns},
            "row_count": len(rows),
            "rows": rows,
        }
        return "workato_smart_list.create_list_from_csv", {"list_name": list_name, "columns": columns}, result

    def workato_smart_list_create_list(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        list_name = resolve_text(raw_input.get("list_name"), self.ctx, state)
        raw_rows = resolve_value(raw_input.get("list_source") or [], self.ctx, state)
        rows = [smart_list_source_row(row) for row in as_list(raw_rows) if isinstance(row, dict)]
        columns = smart_list_row_columns(rows)
        key = _smart_list_key(list_name)
        self.smart_lists[key] = rows
        schema_columns = _smart_list_schema_columns(node)
        if schema_columns:
            # Register declared columns so an EMPTY list still creates its
            # SQLite table (a later query against it must return [], not
            # "no such table").
            self.smart_list_columns[key] = schema_columns
            columns = columns or schema_columns
        result = {
            "ok": True,
            "list_name": list_name,
            "columns": {column: column for column in columns},
            "row_count": len(rows),
            "rows": rows,
        }
        return "workato_smart_list.create_list", {"list_name": list_name}, result

    def workato_smart_list_query(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        sql = resolve_smart_list_sql(raw_input.get("sql"), self.ctx, state)
        rows, source_columns = smart_list_query(sql, self.smart_lists, self.smart_list_columns)
        result_schema = smart_list_columns(raw_input.get("result_schema_json"))
        if re.match(r"\s*(?:CREATE|INSERT|DELETE)\b", sql, flags=re.I):
            # DDL/DML steps carry Workato's placeholder result schema ("a");
            # nothing downstream projects their output — skip alias mapping.
            result_schema = []
        if str(raw_input.get("output_schema_by") or "").lower() == "index" and result_schema:
            # Workato maps result columns to source columns positionally;
            # schema entries beyond the SELECT column count stay absent.
            alias_map = {
                alias: source_columns[i]
                for i, alias in enumerate(result_schema)
                if i < len(source_columns)
            }
        else:
            try:
                alias_map = smart_list_alias_map(result_schema, source_columns)
            except NonRecipeError:
                # Some queries rename columns positionally WITHOUT declaring
                # output_schema_by=index (e.g. [ae_email, group, ae_status]
                # over SELECT assignee_email, group, isActive). When name
                # mapping refuses and the schema fits the SELECT width,
                # Workato's positional semantics apply.
                if len(result_schema) <= len(source_columns):
                    alias_map = {
                        alias: source_columns[i] for i, alias in enumerate(result_schema)
                    }
                else:
                    raise
        projected_rows = smart_list_project_rows(rows, result_schema, alias_map)
        columns = smart_list_row_columns(projected_rows) or result_schema or source_columns
        result = {
            "ok": True,
            "rows": projected_rows,
            "row_count": len(projected_rows),
            "count": len(projected_rows),
            "columns": {column: column for column in columns},
            "column_aliases": alias_map,
        }
        return "workato_smart_list.query_list", {"sql": sql}, result

    def workato_variable_declare_variable(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        variables = raw_input.get("variables") if isinstance(raw_input.get("variables"), dict) else {}
        data = variables.get("data") if isinstance(variables.get("data"), dict) else {}
        args = {"variables": resolve_value(variables, self.ctx, state)}
        result = {
            str(key): None if (value := resolve_value(raw_value, self.ctx, state)) is MISSING else value
            for key, raw_value in data.items()
        }
        # A skip-valued declaration means "not supplied" — the variable is nil
        # (absent), never the sentinel (downstream .present? must be false).
        result = {key: value for key, value in result.items() if value is not SKIP}
        def _walk_schema(entries: Any) -> None:
            for entry in entries or []:
                if not isinstance(entry, dict):
                    continue
                # Schema-declared integer variables coerce ('0' + 2 must be
                # arithmetic 2, not the string '02'); the declaration may sit
                # at top level or nested under variables→data→properties.
                if entry.get("parse_output") == "integer_conversion" and entry.get("name"):
                    state.integer_variable_fields.setdefault(
                        str(node.get("as") or ""), set()
                    ).add(str(entry.get("name")))
                if (
                    entry.get("parse_output") == "integer_conversion"
                    and entry.get("name") in result
                    and isinstance(result[entry.get("name")], str)
                    and result[entry.get("name")].strip() != ""
                ):
                    name = entry.get("name")
                    try:
                        result[name] = int(result[name])
                    except ValueError as exc:
                        raise RawRecipeExecutionError(
                            f"declare_variable {name} is integer-typed but got {result[name]!r}"
                        ) from exc
                _walk_schema(entry.get("properties"))

        _walk_schema(node.get("extended_input_schema"))
        if not data and "value" in raw_input:
            # Alternate raw shape: a bare {name, value} declaration instead of
            # variables.data. Expose the resolved value under both the declared
            # name and "value" so downstream datapills resolve either way.
            value = resolve_value(raw_input.get("value"), self.ctx, state)
            value = None if value is MISSING else value
            name = resolve_text(raw_input.get("name"), self.ctx, state)
            if not name:
                raise NonRecipeError("workato_variable.declare_variable requires a name")
            args = {"name": name, "value": value}
            result = {name: value, "value": value}
        return "workato_runtime.declare_variable", args, result

    def workato_variable_declare_list(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = resolve_value(raw_input, self.ctx, state)
        name = str(raw_input.get("name") or "list")
        list_items = args.get("list_items") if isinstance(args, dict) else []
        if not isinstance(list_items, list):
            list_items = []
        result = {name: list_items, "list_items": list_items}
        if "list" not in result:
            result["list"] = []
        return "workato_runtime.declare_list", args if isinstance(args, dict) else {"input": args}, result

    def workato_variable_update(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            str(key): None if (value := resolve_value(raw_value, self.ctx, state)) is MISSING else value
            for key, raw_value in raw_input.items()
        }
        # input_mode is editor metadata, never a value to assign (a single-field
        # update would otherwise set the variable to the literal "raw").
        result = {key: value for key, value in args.items() if key not in {"name", "input_mode"}}
        target_lines = [line for line in str(args.get("name") or "").splitlines() if line.strip()]
        if len(target_lines) > 1:
            # Multi-target update: each newline-separated target updates its
            # same-named field on its declare step (splitting the whole string
            # on ':' previously wrote one garbage key and set nothing).
            for target in target_lines:
                step_id, field = variable_target(target.strip())
                if not step_id or not field:
                    raise RawRecipeExecutionError(
                        f"multi-target update_variables entry lacks step/field: {target!r}"
                    )
                step_id = _resolve_variable_step_id(state, step_id, field)
                if field not in result:
                    raise RawRecipeExecutionError(
                        f"multi-target update_variables has no resolved input for field {field!r}"
                    )
                target_obj = state.steps.setdefault(step_id, {})
                if not isinstance(target_obj, dict):
                    raise RawRecipeExecutionError(f"variable target step is not an object: {step_id}")
                provider_obj = state.data.setdefault("workato_variable", {}).setdefault(step_id, target_obj)
                if not isinstance(provider_obj, dict):
                    raise RawRecipeExecutionError(f"variable provider target is not an object: {step_id}")
                coerced = _coerce_declared_int(state, step_id, field, result[field])
                target_obj[field] = coerced
                provider_obj[field] = coerced
            return "workato_runtime.update_variables", args, result
        target_step, target_field = variable_target(args.get("name"))
        if target_step:
            target_step = _resolve_variable_step_id(
                state, target_step, target_field or next(iter(result), ""))
            target = state.steps.setdefault(target_step, {})
            if not isinstance(target, dict):
                raise RawRecipeExecutionError(f"variable target step is not an object: {target_step}")
            provider_target = state.data.setdefault("workato_variable", {}).setdefault(target_step, target)
            if not isinstance(provider_target, dict):
                raise RawRecipeExecutionError(f"variable provider target is not an object: {target_step}")
            updates = result if target_field in (None, "") else {target_field: next(iter(result.values()), None)}
            updates = {
                key: _coerce_declared_int(state, target_step, key, value)
                for key, value in updates.items()
            }
            target.update(updates)
            provider_target.update(updates)
        return "workato_runtime.update_variables", args, result

    def workato_variable_update_single(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        # Workato "Update variable" (singular) action: {name, value}. Reuses the
        # plural update_variables target resolution/write semantics; only the
        # runtime trace op name differs.
        _tool, args, result = self.workato_variable_update(node, _ctx, state)
        return "workato_runtime.update_variable", args, result

    def workato_list_create_list(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        # Workato List connector "Create list" action. Two shapes:
        #   {"size": N}          -> a list of N placeholder items, each carrying
        #                           the list size as ____Size (referenced by
        #                           pills like list.first.____Size).
        #   {"list_source": [..]} -> a list built from the provided rows.
        # Downstream pills reference the list under `list`/`list_items`, its
        # size under `size`/`list_size`, and (optionally) the declared `name`.
        raw_input = input_obj(node)
        # Workato's List connector allows an anonymous "Create list" (raw input
        # carries only size/list_source); downstream pills reference it via the
        # default list output. "list" is the harness registry key for that
        # anonymous list, not a data fallback.
        name = resolve_text(raw_input.get("name"), self.ctx, state) or str(raw_input.get("name") or "") or "list"
        if raw_input.get("list_source") is not None:
            raw_rows = resolve_value(raw_input.get("list_source"), self.ctx, state)
            items = [dict(row) for row in as_list(raw_rows) if isinstance(row, dict)]
            size = len(items)
            for item in items:
                item.setdefault("____Size", size)
        else:
            size_value = resolve_value(raw_input.get("size"), self.ctx, state)
            if size_value in (None, MISSING, ""):
                raise RawRecipeExecutionError("workato_list.create_list requires a resolved size or list_source")
            size = int(Decimal(str(size_value)))
            items = [{"____Size": size, "____Index": index} for index in range(size)]
        result: dict[str, Any] = {
            "list": items,
            "list_items": items,
            "size": size,
            "list_size": size,
            "____Size": size,
        }
        if name and name != "list":
            result[name] = items
        return "workato_runtime.create_list", {"name": name, "size": size}, result

    def workato_list_accumulate_list_items(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        # Workato List connector: each invocation (typically inside a foreach)
        # resolves list_item.data and appends it to this step's own accumulated
        # "list_items" output, which downstream steps iterate as a source.
        raw_input = input_obj(node)
        list_item = raw_input.get("list_item") if isinstance(raw_input.get("list_item"), dict) else {}
        data = list_item.get("data") if isinstance(list_item.get("data"), dict) else {}
        resolved = {
            str(key): None if (value := resolve_value(raw_value, self.ctx, state)) is MISSING else value
            for key, raw_value in data.items()
        }
        line = str(node.get("as") or "")
        previous = state.steps.get(line)
        items: list[dict[str, Any]] = (
            list(previous.get("list_items"))
            if isinstance(previous, dict) and isinstance(previous.get("list_items"), list)
            else []
        )
        items.append(resolved)
        result = {"list_items": items, "list_size": len(items)}
        return "workato_runtime.accumulate_list_items", {"list_item": deepcopy(resolved)}, result

    def workato_variable_insert_to_list(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = resolve_value(raw_input, self.ctx, state)
        if not isinstance(args, dict):
            raise RawRecipeExecutionError("workato_variable.insert_to_list input must resolve to an object")
        target_step, target_field = variable_target(args.get("name"))
        item = args.get("list_item", args.get("item", args.get("value", args.get("record", args.get("row")))))
        values = [item]
        result = update_variable_list(state, target_step, target_field, values)
        return "workato_runtime.insert_to_list", args, result

    def workato_variable_insert_to_list_batch(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = resolve_value(raw_input, self.ctx, state)
        if not isinstance(args, dict):
            raise RawRecipeExecutionError("workato_variable.insert_to_list_batch input must resolve to an object")
        target_step, target_field = variable_target(args.get("name"))
        raw_values = args.get("list_items", args.get("items", args.get("values", args.get("records", args.get("rows", [])))))
        values = raw_values if isinstance(raw_values, list) else [raw_values]
        result = update_variable_list(state, target_step, target_field, values)
        return "workato_runtime.insert_to_list_batch", args, result

    def workato_return_result(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {"result": resolve_value(raw_input.get("result") or {}, self.ctx, state)}
        state.return_value = args["result"]
        return call_tool(self.ctx, "workato_recipe_function.return_result", args)

    def workato_api_return_response(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        response = resolve_value(raw_input.get("response") or {}, self.ctx, state)
        args = {
            # Workato's return_response UI defaults the status selector to 200.
            "http_status_code": resolve_text(raw_input.get("http_status_code"), self.ctx, state) or "200",
            "response": action_schema_value(node, "response", response),
        }
        if "response_headers" in raw_input:
            response_headers = resolve_value(
                raw_input.get("response_headers") or {}, self.ctx, state
            )
            args["response_headers"] = action_schema_value(
                node, "response_headers", response_headers
            )
        state.return_value = args["response"]
        return call_tool(self.ctx, "workato_api_platform.return_response", args)

    def workato_service_send_reply(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        # Workato service (callable/API recipe) reply. Not terminal: a service
        # recipe may continue executing after replying to its caller.
        raw_input = input_obj(node)
        reply = resolve_value(raw_input.get("reply") or {}, self.ctx, state)
        args: dict[str, Any] = {
            # Workato's return_result UI defaults the reply type to success.
            "reply_type": resolve_text(raw_input.get("reply_type"), self.ctx, state) or "success",
            "reply": action_schema_value(node, "reply", reply),
        }
        if "message" in raw_input:
            message = resolve_value(raw_input.get("message"), self.ctx, state)
            args["message"] = "" if message is MISSING else message
        state.return_value = {key: value for key, value in args.items()}
        return call_tool(self.ctx, "workato_service.send_reply", args)

    def workato_service_call_service(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        # Workato callable-recipe invocation. The sub-recipe is not executed by
        # the benchmark; its reply is deterministic Workato-internal seed state.
        # The variant seed must carry `workato_service_replies` keyed by this
        # step's `as` id (preferred, exact) or by the called flow_id. Missing
        # keys fail fast — no fallback reply is synthesized.
        raw_input = input_obj(node)
        flow_id = resolve_text(raw_input.get("flow_id"), self.ctx, state)
        request = resolve_value(raw_input.get("request") or {}, self.ctx, state)
        replies = self.seed.get("workato_service_replies")
        if not isinstance(replies, dict):
            raise RawRecipeExecutionError(
                "workato_service.call_service requires seed['workato_service_replies'] "
                "(deterministic Workato-internal sub-recipe replies)"
            )
        step_as = str(node.get("as") or "")
        if step_as in replies:
            reply = replies[step_as]
        elif flow_id and flow_id in replies:
            reply = replies[flow_id]
        else:
            raise RawRecipeExecutionError(
                f"workato_service.call_service reply not seeded for step {step_as!r} / flow {flow_id!r}"
            )
        # The seeded reply is connector output, never a model-selectable input.
        # The reference simulator still needs it to materialize the result, so
        # pass it only to the private execution adapter and record the same
        # public arguments exposed to evaluated agents.
        public_args = {"flow_id": flow_id, "request": request}
        execution_args = {**public_args, "reply": deepcopy(reply)}
        tool, _private_args, result = call_tool(
            self.ctx,
            "workato_service.call_service",
            execution_args,
        )
        return tool, public_args, result

    def workato_service_call_service_async(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        # Async Workato callable-recipe invocation. Unlike the synchronous
        # call_service, async invocation returns no reply data: the sub-recipe
        # runs independently. The benchmark records a deterministic ack only, so
        # no seeded reply is required.
        raw_input = input_obj(node)
        flow_id = resolve_text(raw_input.get("flow_id"), self.ctx, state)
        request = resolve_value(raw_input.get("request") or {}, self.ctx, state)
        args = {"flow_id": flow_id, "request": request}
        return call_tool(self.ctx, "workato_service.call_service_async", args)

    def workato_app_start_recipe(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        return call_tool(self.ctx, "workato_app.start_recipe", {"recipe_id": self._workato_app_recipe_id(node, state)})

    def workato_app_stop_recipe(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        return call_tool(self.ctx, "workato_app.stop_recipe", {"recipe_id": self._workato_app_recipe_id(node, state)})

    def workato_app_rerun_jobs(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        raw_jobs = resolve_value(
            raw_input.get("job_ids", raw_input.get("jobs", raw_input.get("job_id"))),
            self.ctx,
            state,
        )
        raw_job_list = as_list(raw_jobs)
        if any(job in (None, MISSING, "") for job in raw_job_list):
            raise RawRecipeExecutionError("workato_app.rerun_jobs received a nil/blank job id")
        # jobs:[{job_id: ..., recipe_id: ...}] object entries carry the id in
        # job_id (stringifying the dict would corrupt the args).
        job_ids: list[str] = []
        args: dict[str, Any] = {}
        top_recipe_id = resolve_value(raw_input.get("recipe_id"), self.ctx, state)
        if top_recipe_id not in (None, MISSING, ""):
            args["recipe_id"] = str(top_recipe_id)
        for job in raw_job_list:
            if isinstance(job, dict):
                job_id = job.get("job_id") or job.get("id")
                if job_id in (None, MISSING, ""):
                    raise RawRecipeExecutionError("workato_app.rerun_jobs job entry lacks job_id")
                job_ids.append(str(job_id))
                recipe_id = job.get("recipe_id")
                if recipe_id not in (None, MISSING, ""):
                    args.setdefault("recipe_id", str(recipe_id))
            else:
                job_ids.append(str(job))
        args["job_ids"] = job_ids
        return call_tool(self.ctx, "workato_app.rerun_jobs", args)

    def _workato_app_recipe_id(self, node: dict[str, Any], state: RuntimeState) -> str:
        raw_input = input_obj(node)
        recipe_id = resolve_value(
            raw_input.get("recipe_id", raw_input.get("recipe", raw_input.get("id"))),
            self.ctx,
            state,
        )
        if recipe_id in (None, MISSING, ""):
            raise NonRecipeError("workato_app action requires a resolved recipe id")
        return str(recipe_id)

    def workato_app_list_jobs(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args: dict[str, Any] = {}
        recipe_id = resolve_value(raw_input.get("recipe_id"), self.ctx, state)
        if recipe_id not in (None, MISSING, ""):
            args["recipe_id"] = str(recipe_id)
        status = resolve_value(raw_input.get("status"), self.ctx, state)
        if status not in (None, MISSING, ""):
            args["status"] = str(status)
        return call_tool(self.ctx, "workato_app.list_jobs", args)

    def workato_app_get_recipe(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        return call_tool(self.ctx, "workato_app.get_recipe", {"recipe_id": self._workato_app_recipe_id(node, state)})

    def workato_db_table_truncate_table(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {"table_id": resolve_text(raw_input.get("table_id"), self.ctx, state)}
        return call_tool(self.ctx, "workato_db_table.truncate_table", args)

    def workato_pub_sub_publish_to_topic(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            "topic_id": resolve_text(raw_input.get("topic_id"), self.ctx, state),
            "message": resolve_value(raw_input.get("message") or {}, self.ctx, state),
        }
        return call_tool(self.ctx, "workato_pub_sub.publish_to_topic", args)

    def workato_pub_sub_publish_to_topic_batch(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        raw_messages = resolve_value(raw_input.get("messages") or raw_input.get("message") or [], self.ctx, state)
        args = {
            "topic_id": resolve_text(raw_input.get("topic_id"), self.ctx, state),
            "messages": as_list(raw_messages),
        }
        return call_tool(self.ctx, "workato_pub_sub.publish_to_topic_batch", args)

    def workato_genie_return_result(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {"result": resolve_value(raw_input.get("result") or {}, self.ctx, state)}
        state.return_value = args["result"]
        return call_tool(self.ctx, "workato_genie.workflow_return_result", args)

    def salesforce_search(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        query = resolve_text(raw_input.get("query"), self.ctx, state)
        sobject = salesforce_sobject(query) or str(raw_input.get("sobject_name") or "")
        filters: list[dict[str, Any]] = []
        metadata_keys = {
            "advanced",
            "field_list",
            "include_combined_attachments",
            "limit",
            "object",
            "object_name",
            "offset",
            "order_by",
            "output_schema",
            "parameters",
            "query",
            "query_all",
            "sobject",
            "sobject_name",
            "soql_query",
            "soql_query_where_clause",
            "table_list",
            "table_list_custom",
        }
        for key, raw_value in raw_input.items():
            if key in metadata_keys:
                continue
            resolved = resolve_value(raw_value, self.ctx, state)
            if resolved is SKIP or resolved is MISSING:
                continue
            if present(resolved):
                filters.append({"field": str(key), "value": resolved})
        args: dict[str, Any] = {"sobject": sobject, "query": query}
        limit = resolve_value(raw_input.get("limit"), self.ctx, state)
        if present(limit):
            # The public benchmark trace has one JSON representation for
            # numeric pagination values. Workato exports editor numbers as
            # strings, but the connector receives an integer.
            args["limit"] = canonical_optional_integer(limit)
        if filters:
            args["filters"] = filters
        tool, tool_args, result = call_tool(self.ctx, "salesforce.search_records", args)
        integer_fields = _integer_conversion_fields(node)
        if integer_fields and isinstance(result, dict):
            # Node output schema declares integer_conversion: live SF returns
            # Number fields as floats (5.0) where Workato renders 5.
            for row in as_list(result.get("records")):
                if not isinstance(row, dict):
                    continue
                for field in integer_fields:
                    for target in (row, row.get("fields") if isinstance(row.get("fields"), dict) else None):
                        if target and isinstance(target.get(field), float) and target[field].is_integer():
                            target[field] = int(target[field])
        return tool, tool_args, result

    def salesforce_get(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        record_id = resolve_value(raw_input.get("id"), self.ctx, state)
        sobject = resolve_text(raw_input.get("sobject_name") or raw_input.get("object_name") or raw_input.get("object"), self.ctx, state)
        tool, args, search_result = call_tool(
            self.ctx,
            "salesforce.search_records",
            {
                "sobject": sobject,
                "query": "",
                "filters": [{"field": "Id", "value": record_id}],
                "limit": 1,
            },
        )
        records = search_result.get("records") if isinstance(search_result.get("records"), list) else []
        if not records:
            # Workato's get returns EMPTY output for a missing record (pills
            # resolve nil downstream); it does not error the job.
            return tool, args, {"ok": True}
        record = dict(records[0])
        record.setdefault("ok", True)
        return tool, args, record

    def salesforce_update(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        sobject = resolve_text(raw_input.get("sobject_name") or raw_input.get("object_name") or raw_input.get("object"), self.ctx, state)
        if "records" in raw_input:
            records = resolve_value(raw_input.get("records"), self.ctx, state)
            update_args: list[dict[str, Any]] = []
            for record in as_list(records):
                if not isinstance(record, dict):
                    raise RawRecipeExecutionError("Salesforce composite update record must resolve to an object")
                record_id = record.get("Id") or record.get("id")
                fields = {
                    str(key): value
                    for key, value in record.items()
                    if str(key) not in {"Id", "id", "attributes", "____source"}
                    # Workato nil-compaction (same as the single-record
                    # path): nil mapped fields are omitted, never null'd;
                    # genuine '' is sent.
                    and value is not None
                }
                args = {"sobject": sobject, "id": record_id, "fields": fields}
                update_args.append(args)
            # Composite Workato actions compile to one public batch call in
            # every variant.  Cardinality must not change the tool-call shape
            # (one record used to look like a scalar update, while two records
            # looked like an aggregate), because the frozen recipe plan is
            # recipe-level rather than variant-level.
            return call_tool(
                self.ctx,
                "salesforce.update_record",
                {"sobject": sobject, "records": update_args},
            )
        metadata_keys = {
            "advanced",
            "advanced_configuration",
            "batch_size",
            "id",
            "object",
            "object_name",
            "output_schema",
            "parameters",
            "records",
            "sobject",
            "sobject_name",
        }
        fields: dict[str, Any] = {}
        for key, raw_value in raw_input.items():
            if key in metadata_keys:
                continue
            resolved = resolve_value(raw_value, self.ctx, state)
            if resolved is SKIP or resolved is MISSING:
                continue
            if resolved is None:
                # Workato compacts NIL optional inputs out of the request
                # (e.g. `.presence` of an absent pill) — it never PATCHes
                # null without an explicit clear. A genuinely ''-valued pill
                # IS sent (input.compact removes nil only), so '' passes
                # through. Live-evidenced by 131787576's status-absent
                # variant (Lead update args carry Description only; Status
                # nil-compacted out, read-back Status equals the seed).
                continue
            fields[str(key)] = resolved
        args = {
            "sobject": sobject,
            "id": resolve_value(raw_input.get("id"), self.ctx, state),
            "fields": fields,
        }
        return call_tool(self.ctx, "salesforce.update_record", args)

    def salesforce_create(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        sobject = resolve_text(raw_input.get("sobject_name") or raw_input.get("object_name") or raw_input.get("object"), self.ctx, state)
        metadata_keys = {
            "advanced",
            "advanced_configuration",
            "object",
            "object_name",
            "output_schema",
            "parameters",
            "sobject",
            "sobject_name",
        }
        fields: dict[str, Any] = {}
        for key, raw_value in raw_input.items():
            if key in metadata_keys:
                continue
            resolved = resolve_value(raw_value, self.ctx, state)
            if resolved is SKIP or resolved is MISSING:
                continue
            if resolved is None:
                # Workato nil-compaction — see salesforce_update.
                continue
            fields[str(key)] = resolved
        args = {"sobject": sobject, "fields": fields}
        return call_tool(self.ctx, "salesforce.create_record", args)

    def salesforce_upsert(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        sobject = resolve_text(raw_input.get("sobject_name") or raw_input.get("object_name") or raw_input.get("object"), self.ctx, state)
        query_field = raw_input.get("query_field") if isinstance(raw_input.get("query_field"), dict) else {}
        key_field = resolve_text(query_field.get("primary_key"), self.ctx, state)
        metadata_keys = {
            "advanced",
            "advanced_configuration",
            "object",
            "object_name",
            "output_schema",
            "parameters",
            "query_field",
            "sobject",
            "sobject_name",
        }
        fields: dict[str, Any] = {}
        for key, raw_value in raw_input.items():
            if key in metadata_keys:
                continue
            resolved = resolve_value(raw_value, self.ctx, state)
            if resolved is SKIP or resolved is MISSING:
                continue
            if resolved is None:
                # Workato nil-compaction — see salesforce_update.
                continue
            fields[str(key)] = resolved
        args = {"sobject": sobject, "key_field": key_field, "fields": fields}
        return call_tool(self.ctx, "salesforce.upsert_record", args)

    def logger_log_message(self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState) -> tuple[str, dict[str, Any], dict[str, Any]]:
        raw_input = input_obj(node)
        args = {
            "message": resolve_text(raw_input.get("message"), self.ctx, state),
            "log_level": str(raw_input.get("log_level") or "INFO").upper(),
            "user_logs_enabled": truthy(raw_input.get("user_logs_enabled", True)),
        }
        return "workato_runtime.log_message", args, {"ok": True, **args}


def execute_raw_recipe(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    return RawWorkatoRuntime(ctx, seed).execute(raw)


def _sheet_headers(value: Any) -> list[str]:
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _sheet_column_labels(node: dict[str, Any]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for schema in node.get("extended_input_schema") or []:
        if not isinstance(schema, dict) or schema.get("name") not in {"columns", "data", "rows"}:
            continue
        for prop in schema.get("properties") or []:
            if not isinstance(prop, dict):
                continue
            name = str(prop.get("name") or "")
            label = str(prop.get("label") or "")
            if name and label:
                labels[name] = label
    return labels


TERMINAL_TOOLS = {
    "workato_api_platform.return_response",
    "workato_genie.workflow_return_result",
    "workato_recipe_function.return_result",
}


def input_obj(node: dict[str, Any]) -> dict[str, Any]:
    raw = node.get("input") or {}
    if not isinstance(raw, dict):
        raise RawRecipeExecutionError("raw input must be an object")
    return raw


def call_tool(ctx: RecipeContext, name: str, args: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    result = ctx.tools.call(name, args)
    return name, args, result


def trigger_output(seed: dict[str, Any]) -> dict[str, Any]:
    # The trigger key must be explicitly present. An explicitly-empty {} is a
    # declared payload-less trigger (e.g. scheduler ticks); absence is an
    # authoring error.
    if "trigger" not in seed:
        raise NonRecipeError("seed is missing the explicit trigger payload")
    trigger = seed.get("trigger")
    if not isinstance(trigger, dict):
        raise NonRecipeError("seed trigger payload must be an object")
    return dict(trigger)


def resolved_parameters(raw_input: dict[str, Any], ctx: RecipeContext, state: RuntimeState) -> dict[str, Any]:
    parameters = raw_input.get("parameters") or {}
    if not isinstance(parameters, dict):
        raise RawRecipeExecutionError("parameters must be an object")
    out: dict[str, Any] = {}
    for key, value in parameters.items():
        resolved = resolve_value(value, ctx, state)
        if resolved is SKIP:
            continue
        out[str(key)] = None if resolved is MISSING else resolved
    return out


def primary_field_id(
    raw_primary: Any,
    record: dict[str, Any],
    state: RuntimeState,
    node: dict[str, Any] | None = None,
) -> str:
    primary = str(raw_primary or "")
    if primary and not primary.startswith("<anon>"):
        return primary
    schema_primary = schema_primary_field_id(node, record)
    if schema_primary:
        return schema_primary
    raise NonRecipeError(
        "primary_field_id is missing/anonymous and the node schema declares no primary key; "
        "refusing to guess"
    )


def schema_primary_field_id(node: dict[str, Any] | None, record: dict[str, Any]) -> str:
    if not isinstance(node, dict):
        return ""
    selection = node.get("dynamicPickListSelection")
    if not isinstance(selection, dict):
        return ""
    label = str(selection.get("primary_field_id") or "").strip().lower()
    if not label:
        return ""
    for schema in node.get("extended_input_schema") or []:
        if not isinstance(schema, dict) or schema.get("name") != "parameters":
            continue
        for prop in schema.get("properties") or []:
            if not isinstance(prop, dict):
                continue
            name = str(prop.get("name") or "")
            prop_label = str(prop.get("label") or "").strip().lower()
            if name in record and prop_label == label:
                return name
    return ""


def workato_db_filters(raw_input: dict[str, Any], ctx: RecipeContext, state: RuntimeState) -> list[dict[str, Any]]:
    filters: list[dict[str, Any]] = []
    for raw_filter in raw_input.get("filters") or []:
        if not isinstance(raw_filter, dict):
            raise RawRecipeExecutionError("workato_db_table filter must be an object")
        raw_field = raw_filter.get("field_id")
        if raw_field in (None, ""):
            if any(raw_filter.get(key) not in (None, "") for key in ("value", "op", "value_default")):
                raise RawRecipeExecutionError("workato_db_table filter missing field_id")
            # A fully-empty trailing {} slot mirrors Workato ignoring blank rows.
            continue
        raw_value = raw_filter.get("value")
        op = raw_filter.get("op")
        if raw_value is None and "value_default" in raw_filter:
            raw_value = raw_filter.get("value_default")
            op = op or raw_filter.get("op_default")
        if raw_value is None and "value_relation" in raw_filter:
            raw_value = raw_filter.get("value_relation")
            op = op or raw_filter.get("op_relation")
        if raw_value is None and "value_integer" in raw_filter:
            raw_value = raw_filter.get("value_integer")
            op = op or raw_filter.get("op_integer")
        if raw_value is None and "value_date_time" in raw_filter:
            raw_value = raw_filter.get("value_date_time")
            op = op or raw_filter.get("op_date_time")
        if raw_value is None and "value_date" in raw_filter:
            raw_value = raw_filter.get("value_date")
            op = op or raw_filter.get("op_date")
        if raw_value is None and "op_boolean" in raw_filter:
            op_boolean = str(raw_filter.get("op_boolean") or "").lower()
            if op_boolean == "istrue":
                raw_value = True
            elif op_boolean == "isfalse":
                raw_value = False
            else:
                raise NonRecipeError(f"unsupported workato_db_table boolean filter op: {op_boolean}")
            op = "eq"
        if op in (None, ""):
            # Null-check ops carry no value key at all, e.g.
            # {"field_id": ..., "op_date_time": "isnotnull"}.
            for key, kind_op in raw_filter.items():
                if key.startswith("op") and str(kind_op) in {"isnull", "isnotnull"}:
                    op = str(kind_op)
                    break
        canonical_op = str(
            op
            or raw_filter.get("op_default")
            or raw_filter.get("op_relation")
            or raw_filter.get("op_integer")
            or "eq"
        ).lower()
        if canonical_op == "equals":
            canonical_op = "eq"
        value = resolve_value(raw_value, ctx, state)
        if value is MISSING:
            # Only a genuinely UNKNOWN source/pill fails fast. A pill that
            # nil-propagates (source ran, path walked through nil/empty — see
            # lookup_path) arrives as None and is a faithful NULL filter
            # value: the mock comparator treats None as "" comparable, so an
            # eq-null filter matches only null/empty cells (Workato parity).
            raise RawRecipeExecutionError(f"workato_db_table filter value missing for field {raw_field}")
        filters.append(
            {
                "field_id": normalize_workato_field_id(str(raw_field)),
                "op": canonical_op,
                "value": strip_anon_wrapper(value),
            }
        )
    return filters


def strip_anon_wrapper(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("<anon>") and value.endswith("</anon>"):
        return value[len("<anon>"):-len("</anon>")]
    return value


def snowflake_parameters(raw_input: dict[str, Any], ctx: RecipeContext, state: RuntimeState) -> dict[str, Any]:
    raw_parameters = raw_input.get("parameters") or {}
    if not isinstance(raw_parameters, dict):
        return {}
    data = raw_parameters.get("data") if isinstance(raw_parameters.get("data"), dict) else {}
    out: dict[str, Any] = {}
    for key, raw_value in data.items():
        resolved = resolve_value(raw_value, ctx, state)
        out[str(key)] = None if resolved is MISSING else resolved
    return out


def canonical_optional_integer(value: Any) -> int | None:
    """Project an editor numeric field to the canonical connector JSON type."""

    if value in (None, MISSING, SKIP, ""):
        return None
    try:
        return int(Decimal(str(value)))
    except (ArithmeticError, ValueError) as exc:
        raise RawRecipeExecutionError(
            f"expected an integer-compatible connector value, got {value!r}"
        ) from exc


def snowflake_primary_key_columns(node: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for schema in node.get("extended_input_schema") or []:
        if not isinstance(schema, dict):
            continue
        for prop in schema.get("properties") or []:
            if not isinstance(prop, dict):
                continue
            details = prop.get("details") if isinstance(prop.get("details"), dict) else {}
            if details.get("primary_key") is True:
                name = details.get("column_name") or prop.get("name")
                if name:
                    keys.append(str(name))
    return keys


def _sql_has_top_level_order_by(sql: str) -> bool:
    """True only for a paren-depth-0 ORDER BY, honoring single-quoted strings."""
    text = str(sql)
    depth = 0
    quote = False
    idx = 0
    while idx < len(text):
        char = text[idx]
        if quote:
            if char == "'":
                quote = False
            idx += 1
            continue
        if char == "'":
            quote = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif (
            depth == 0
            and re.match(r"ORDER\s+BY\b", text[idx:], flags=re.I)
            and (idx == 0 or not (text[idx - 1].isalnum() or text[idx - 1] == "_"))
        ):
            return True
        idx += 1
    return False


def resolve_zone_info(zone: str) -> "zoneinfo.ZoneInfo":
    """Inline anonymizer tags in zone names are corpus artifacts
    ('<anon>Europe/London</anon>'); the inner text is the semantic zone.
    Invalid zones (including anonymizer fiction like Asia/Osaka) fail fast
    with the cleaned name in the message."""
    cleaned = re.sub(r"<anon>(.*?)</anon>", r"\1", str(zone or ""))
    try:
        return zoneinfo.ZoneInfo(cleaned)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError) as exc:
        raise RawRecipeExecutionError(f"unknown time zone: {cleaned!r}") from exc


def normalize_workato_field_id(field_id: str) -> str:
    return field_id.replace("-", "_")


def salesforce_sobject(query: str) -> str:
    # The outer query's FROM, not a SELECT-list/IN subquery's: drop every
    # parenthesized segment (subqueries always sit inside parens) first.
    text = str(query or "")
    while True:
        stripped = re.sub(r"\([^()]*\)", " ", text)
        if stripped == text:
            break
        text = stripped
    match = re.search(r"\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)", text, flags=re.I)
    return match.group(1) if match else ""


def salesforce_select_fields(query: str) -> list[str]:
    match = re.search(r"\bSELECT\s+(.+?)\s+\bFROM\b", str(query or ""), flags=re.I | re.S)
    if not match:
        return []
    fields: list[str] = []
    for raw in re.split(r",|\n", match.group(1)):
        field = raw.strip()
        if field:
            fields.append(field)
    return fields


def _record_field(row: dict[str, Any], field: str) -> Any:
    value = field_value(row, field)
    return "" if value is MISSING or value is None else value


def smart_list_columns(raw_schema: Any) -> list[str]:
    schema = raw_schema
    if isinstance(raw_schema, str):
        try:
            schema = json.loads(raw_schema)
        except json.JSONDecodeError as exc:
            raise NonRecipeError(f"invalid smart list csv_schema_json: {exc}") from exc
    if not isinstance(schema, list):
        raise NonRecipeError("smart list csv_schema_json must be a JSON list")
    columns: list[str] = []
    for item in schema:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if name:
            columns.append(name)
    return columns


def smart_list_rows_from_csv(csv_text: str, columns: list[str], has_headers: bool) -> list[dict[str, Any]]:
    if not str(csv_text or "").strip():
        return []
    reader = csv.reader(io.StringIO(str(csv_text)))
    rows = list(reader)
    if not rows:
        return []
    active_columns = list(columns)
    start_idx = 0
    if has_headers:
        active_columns = [str(value or "").strip() for value in rows[0]]
        start_idx = 1
    out: list[dict[str, Any]] = []
    for raw_row in rows[start_idx:]:
        if not raw_row:
            continue
        record: dict[str, Any] = {}
        for idx, column in enumerate(active_columns):
            if not column:
                continue
            record[column] = raw_row[idx] if idx < len(raw_row) else ""
        out.append(record)
    return out


def smart_list_source_row(row: dict[str, Any]) -> dict[str, Any]:
    fields = row.get("fields")
    if isinstance(fields, dict):
        out = dict(fields)
        if "Id" not in out and row.get("id") not in (None, ""):
            out["Id"] = row.get("id")
        return out
    return dict(row)


def smart_list_row_columns(rows: list[dict[str, Any]]) -> list[str]:
    columns: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in row:
            text = str(key)
            if text not in columns:
                columns.append(text)
    return columns


def _smart_list_key(name: Any) -> str:
    return str(name or "").strip().lower()


def _smart_list_declared_columns(
    key: str,
    rows: list[dict[str, Any]],
    table_columns: dict[str, list[str]] | None,
) -> list[str]:
    """Column order for SELECT * results: declared list columns first (real
    Workato returns declared order, which by-index schema mapping relies on),
    then any extra row keys, case-insensitively deduped (snowflake read-back
    rows carry UPPER+lower pairs)."""
    columns = list((table_columns or {}).get(key) or [])
    for column in smart_list_row_columns(rows):
        if column not in columns:
            columns.append(column)
    seen_lower: set[str] = set()
    deduped: list[str] = []
    for column in columns:
        if column.lower() in seen_lower:
            continue
        seen_lower.add(column.lower())
        deduped.append(column)
    return deduped


def _resolve_variable_step_id(state: RuntimeState, step_id: str, field_name: str = "") -> str:
    """Inconsistent anonymization can tag an update target (`<anon>b…</anon>`)
    while the declare step registered untagged — setdefault would then write a
    phantom step and the declared variable would never change. Verbatim id
    wins (self-consistently tagged recipes stay intact); the anon-stripped id
    is only a fallback to an EXISTING step. When the anonymizer replaced the
    id with a PLACEHOLDER token (stripping yields nothing declared), the only
    faithful resolution is by the updated field's unique declaring step —
    ambiguity or no owner is a hard error, never a phantom write."""
    if step_id in state.steps:
        return step_id
    stripped = strip_anon_wrapper(step_id)
    if stripped != step_id and stripped in state.steps:
        return stripped
    if "<anon>" in step_id:
        variables = state.data.get("workato_variable", {})
        owners = [sid for sid, obj in variables.items()
                  if isinstance(obj, dict) and field_name and field_name in obj]
        if len(owners) == 1:
            return owners[0]
        if len(owners) > 1:
            raise RawRecipeExecutionError(
                f"anonymized variable target {step_id!r} does not resolve: "
                f"field {field_name!r} has {len(owners)} declared owners"
            )
        # 0 owners: schema-only declares (variables.schema without data) leave
        # an empty result dict, so field ownership cannot identify them. The
        # reads in that class use the SAME tagged line — the verbatim tagged
        # id is the self-consistent store (111834972 class).
    return step_id


def _coerce_declared_int(state: RuntimeState, step_id: str, field_name: str, value: Any) -> Any:
    """Coerce an update_variables write to int when the target declare step's
    schema marked the field integer_conversion — otherwise counter formulas
    like `=_dp(num) + 1` string-join on the second iteration ('1' + 1 → '11'):
    arithmetic results are engine-canonical strings and the declare-time
    coercion never sees them."""
    if field_name not in state.integer_variable_fields.get(step_id, set()):
        return value
    if isinstance(value, str) and value.strip() != "":
        try:
            return int(value)
        except ValueError as exc:
            raise RawRecipeExecutionError(
                f"update_variables {field_name} is integer-typed but got {value!r}"
            ) from exc
    return value


def _sheets_schema_col_names(node: dict[str, Any]) -> list[str]:
    """col_-prefixed output-schema names declared on a sheets node."""
    names: list[str] = []

    def walk(entries: Any) -> None:
        for entry in entries or []:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name") or "")
            if name.startswith("col_"):
                names.append(name)
            walk(entry.get("properties"))

    walk(node.get("extended_output_schema"))
    return names


def _integer_conversion_fields(node: dict[str, Any]) -> list[str]:
    """Field names whose node output schema declares parse_output
    integer_conversion (recursively through nested properties)."""
    out: list[str] = []

    def walk(entries: Any) -> None:
        for entry in entries or []:
            if not isinstance(entry, dict):
                continue
            if entry.get("parse_output") == "integer_conversion" and entry.get("name"):
                out.append(str(entry["name"]))
            walk(entry.get("properties"))

    walk(node.get("extended_output_schema"))
    walk(node.get("output_schema"))
    return out


def _schema_wraps_array(node: dict[str, Any]) -> bool:
    """True when the node's extended_output_schema declares `document` as an
    object whose only property is `array` (Workato's top-level-array wrap)."""
    schema = node.get("extended_output_schema")
    if not isinstance(schema, list):
        return False
    for entry in schema:
        if isinstance(entry, dict) and entry.get("name") == "document":
            properties = entry.get("properties")
            return (
                isinstance(properties, list)
                and len(properties) == 1
                and isinstance(properties[0], dict)
                and properties[0].get("name") == "array"
            )
    return False


def _smart_list_schema_columns(node: dict[str, Any]) -> list[str]:
    """Column names declared by a create_list node's extended_output_schema
    ("columns" entry -> properties[].name)."""
    schema = node.get("extended_output_schema")
    if not isinstance(schema, list):
        return []
    for entry in schema:
        if isinstance(entry, dict) and entry.get("name") == "columns":
            return [
                str(prop.get("name"))
                for prop in entry.get("properties") or []
                if isinstance(prop, dict) and prop.get("name")
            ]
    return []


def resolve_smart_list_sql(raw_sql: Any, ctx: RecipeContext, state: RuntimeState) -> str:
    if isinstance(raw_sql, str) and raw_sql.startswith("="):
        # Formula-mode sql (concat/format_map/ternary over pills) — evaluate
        # the whole expression; pill-substituting the raw bytes would feed a
        # leading '=' straight to sqlite. A SKIP/nil result means no query.
        resolved = eval_formula(raw_sql, ctx, state)
        if resolved is MISSING or resolved is SKIP or resolved is None:
            return ""
        return str(resolved)
    if not isinstance(raw_sql, str):
        resolved = resolve_value(raw_sql, ctx, state)
        return "" if resolved is MISSING else str(resolved or "")

    quote_mask = _single_quote_mask(raw_sql)

    def replace_datapill(match: re.Match[str]) -> str:
        raw = match.group(1)
        try:
            pill = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RawRecipeExecutionError(f"invalid datapill JSON: {raw}") from exc
        inside_quotes = quote_mask[match.start()]
        if (
            not inside_quotes
            and pill.get("pill_type") == "output"
            and pill.get("provider") == "workato_smart_list"
        ):
            # Unquoted pills name COLUMNS (SELECT #{pill} / FROM #{list}); a
            # pill inside single quotes is a VALUE literal ('#{row.field}')
            # and must resolve through the generic path below.
            path = pill.get("path") if isinstance(pill.get("path"), list) else []
            if len(path) >= 2 and path[0] == "columns":
                return str(path[1])
            if (
                len(path) >= 3
                and path[0] == "rows"
                and isinstance(path[1], dict)
                and path[1].get("path_element_type") == "current_item"
            ):
                line = str(pill.get("line") or "")
                step = state.steps.get(line, MISSING)
                alias_map = step.get("column_aliases") if isinstance(step, dict) else {}
                alias = str(path[2])
                if isinstance(alias_map, dict) and alias in alias_map:
                    return str(alias_map[alias])
        value = resolve_dp_json(raw, ctx, state)
        return ruby_to_s(value)

    return _DP_RE.sub(replace_datapill, raw_sql)


def smart_list_query(
    sql: str,
    smart_lists: dict[str, list[dict[str, Any]]],
    table_columns: dict[str, list[str]] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    # Normalize whitespace and drop a trailing statement terminator (";").
    text = " ".join(str(sql or "").split()).rstrip(" ;")

    # CREATE TABLE <name> (<col> <type>, ...) -> register an empty list and
    # remember the column order for positional INSERTs.
    create = re.fullmatch(r"CREATE\s+TABLE\s+([A-Za-z_][A-Za-z0-9_ ]*?)\s*\((.*)\)", text, flags=re.I | re.S)
    if create:
        name = create.group(1).strip()
        columns = [part.strip().split()[0] for part in _split_sql_top_level(create.group(2), ",") if part.strip()]
        key = _smart_list_key(name)
        smart_lists[key] = []
        if table_columns is not None:
            table_columns[key] = columns
        return [], columns

    # INSERT INTO <name> [(cols)] VALUES (v1,..),(v2,..) -> append positional rows.
    insert = re.fullmatch(
        r"INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_ ]*?)\s*(?:\(([^)]*)\))?\s*VALUES\s*(.+)",
        text,
        flags=re.I | re.S,
    )
    if insert:
        name = insert.group(1).strip()
        key = _smart_list_key(name)
        explicit_columns = [col.strip() for col in insert.group(2).split(",")] if insert.group(2) else None
        columns = explicit_columns or (table_columns or {}).get(key) or []
        rows = smart_lists.setdefault(key, [])
        inserted: list[dict[str, Any]] = []
        for group in re.findall(r"\(([^)]*)\)", insert.group(3)):
            cells = [_smart_list_sql_literal(cell.strip()) for cell in _split_sql_top_level(group, ",")]
            if columns:
                row = {columns[i]: (cells[i] if i < len(cells) else None) for i in range(len(columns))}
            else:
                row = {f"col{i + 1}": cell for i, cell in enumerate(cells)}
            rows.append(row)
            inserted.append(dict(row))
        return inserted, columns or smart_list_row_columns(rows)

    # SELECT rowid FROM <name> -> 1-based row ids.
    rowid = re.fullmatch(r"SELECT\s+rowid\s+FROM\s+([A-Za-z_][A-Za-z0-9_ ]*)", text, flags=re.I)
    if rowid:
        rows = smart_lists.get(_smart_list_key(rowid.group(1).strip()), [])
        return [{"rowid": index + 1} for index in range(len(rows))], ["rowid"]

    # SELECT <col> FROM <A> UNION SELECT <col> FROM <B> -> distinct single-column rows.
    union = re.fullmatch(
        r"SELECT\s+(\S+)\s+FROM\s+([A-Za-z_][A-Za-z0-9_ ]*?)\s+UNION\s+"
        r"SELECT\s+(\S+)\s+FROM\s+([A-Za-z_][A-Za-z0-9_ ]*)",
        text,
        flags=re.I,
    )
    if union:
        out_column = union.group(1).lower()
        seen: set[str] = set()
        combined: list[dict[str, Any]] = []
        for column, list_name in ((union.group(1), union.group(2)), (union.group(3), union.group(4))):
            for row in smart_lists.get(_smart_list_key(list_name.strip()), []):
                value = field_value(row, column)
                marker = str(value)
                if marker in seen:
                    continue
                seen.add(marker)
                combined.append({out_column: value})
        return combined, [out_column]

    match = re.fullmatch(
        r"SELECT\s+A\.([A-Za-z_][A-Za-z0-9_]*)\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)\s+AS\s+A\s+"
        r"WHERE\s+A\.\1\s+NOT\s+IN\s+\(SELECT\s+B\.([A-Za-z_][A-Za-z0-9_]*)\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)\s+AS\s+B\)",
        text,
        flags=re.I,
    )
    if match:
        left_field = match.group(1)
        left_list = smart_lists.get(_smart_list_key(match.group(2)), [])
        right_field = match.group(3)
        right_list = smart_lists.get(_smart_list_key(match.group(4)), [])
        excluded = {
            str(value)
            for row in right_list
            if (value := field_value(row, right_field)) not in (None, "", MISSING)
        }
        out: list[dict[str, Any]] = []
        for row in left_list:
            value = field_value(row, left_field)
            if value in (None, "", MISSING) or str(value) in excluded:
                continue
            out.append({left_field.lower(): value})
        return out, [left_field.lower()]

    # Advanced SQL (JOINs, aggregates, ORDER BY, subqueries, quoted names,
    # top-level OR, …) is served by a real in-memory SQLite engine — the
    # dialect Workato smart lists actually speak (JULIANDAY, rowid, quoted
    # identifiers). This routing MUST run before the compound/projected/bare
    # regex branches below: those branches silently mis-evaluate such queries
    # (e.g. a bare SELECT swallows "ORDER BY x" into the table name and
    # returns [], and COUNT(*) projects a null column) instead of failing.
    if _SMART_SQL_ENGINE_RE.search(text) or _smart_list_top_level_or_where(text):
        return _smart_list_sqlite_query(text, smart_lists, table_columns)

    compound = re.fullmatch(
        r"SELECT\s+\*\s+FROM\s+(.+?)\s+WHERE\s+(.+)",
        text,
        flags=re.I | re.S,
    )
    if compound:
        list_name = compound.group(1).strip()
        conditions = _smart_list_where_conditions(compound.group(2))
        if conditions is not None:
            key = _smart_list_key(list_name)
            rows = smart_lists.get(key, [])
            out = [
                dict(row)
                for row in rows
                if all(smart_list_row_matches(row, field, op, expected) for field, op, expected in conditions)
            ]
            return out, _smart_list_declared_columns(key, rows, table_columns)

    # Column-projected SELECT with an optional parenthesized OR/IN group in the
    # WHERE clause, e.g.
    #   SELECT a, b FROM T WHERE x='1' AND (y IN ('m','n') OR z='p')
    # Handles both '*' and named-column projection; simple AND-only WHEREs on
    # 'SELECT *' are already served by the compound branch above.
    projected = re.fullmatch(
        r"SELECT\s+(.+?)\s+FROM\s+([A-Za-z_][A-Za-z0-9_ ]*?)\s+WHERE\s+(.+)",
        text,
        flags=re.I | re.S,
    )
    if projected:
        columns_raw = projected.group(1).strip()
        list_name = projected.group(2).strip()
        where = projected.group(3).strip()
        key = _smart_list_key(list_name)
        rows = smart_lists.get(key, [])
        matched = [row for row in rows if _smart_list_where_matches(row, where)]
        if columns_raw == "*":
            return [dict(row) for row in matched], _smart_list_declared_columns(key, rows, table_columns)
        columns = [column.strip() for column in columns_raw.split(",") if column.strip()]
        out = [{column: field_value(row, column) for column in columns} for row in matched]
        return out, columns

    # List names may contain spaces (e.g. created via create_list as "Opportunity Entries").
    bare = re.fullmatch(r"SELECT\s+\*\s+FROM\s+([A-Za-z_][A-Za-z0-9_ ]*)", text, flags=re.I)
    if bare and not re.search(r"\bWHERE\b", bare.group(1), flags=re.I):
        key = _smart_list_key(bare.group(1))
        rows = smart_lists.get(key, [])
        return [dict(row) for row in rows], _smart_list_declared_columns(key, rows, table_columns)

    update = re.fullmatch(
        r"UPDATE\s+(.+?)\s+SET\s+([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*('[^']*'|\"[^\"]*\"|[^\s]+)\s+"
        r"WHERE\s+([A-Za-z_][A-Za-z0-9_.]*)\s+(?:(IN)\s*\(([^)]*)\)|(=)\s*('[^']*'|\"[^\"]*\"|[^\s]+))",
        text,
        flags=re.I | re.S,
    )
    if update:
        list_name = update.group(1).strip()
        set_field = update.group(2)
        set_value = _smart_list_sql_literal(update.group(3))
        where_field = update.group(4)
        rows = smart_lists.get(_smart_list_key(list_name), [])
        if update.group(5):  # IN (...)
            allowed = {
                _smart_list_sql_literal(part.strip())
                for part in update.group(6).split(",")
                if part.strip()
            }
            matches = lambda row: str(field_value(row, where_field)) in allowed  # noqa: E731
        else:  # = literal
            expected = _smart_list_sql_literal(update.group(8))
            matches = lambda row: smart_list_row_matches(row, where_field, "=", expected)  # noqa: E731
        updated: list[dict[str, Any]] = []
        for row in rows:
            if matches(row):
                row[set_field] = set_value
                updated.append(dict(row))
        return updated, smart_list_row_columns(rows)

    # Last resort before failing: shapes none of the exact-match branches
    # recognise (complex UPDATE WHEREs, DELETEs, …) go to the SQLite engine,
    # which raises NonRecipeError itself if the SQL is genuinely unsupported.
    return _smart_list_sqlite_query(text, smart_lists, table_columns)


# Query features that the regex fast paths above either reject or — worse —
# silently mis-evaluate. Any hit routes the query to the SQLite engine.
_SMART_SQL_ENGINE_RE = re.compile(
    r"\bJOIN\b|\bDISTINCT\b|\bGROUP\s+BY\b|\bORDER\s+BY\b|\bHAVING\b"
    r"|\bNOT\s+LIKE\b|\bIS\s+(?:NOT\s+)?NULL\b|\bNOT\s+IN\b|\bLIMIT\b"
    r"|\(\s*SELECT\b|^\s*WITH\b|^\s*DELETE\b"
    r"|\b(?:COUNT|SUM|AVG|MIN|MAX|GROUP_CONCAT|JULIANDAY|COALESCE|CAST|LOWER|UPPER)\s*\("
    r'|(?:FROM|JOIN|INTO|UPDATE)\s+"',
    flags=re.I,
)

_SQLITE_MUTATION_RE = re.compile(
    r"\s*(?:UPDATE\s+(\"[^\"]+\"|[A-Za-z_][A-Za-z0-9_]*)"
    r"|INSERT\s+INTO\s+(\"[^\"]+\"|[A-Za-z_][A-Za-z0-9_]*)"
    r"|DELETE\s+FROM\s+(\"[^\"]+\"|[A-Za-z_][A-Za-z0-9_]*)"
    r"|CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\"[^\"]+\"|[A-Za-z_][A-Za-z0-9_]*))",
    flags=re.I,
)


def _smart_list_top_level_or_where(text: str) -> bool:
    """True when a WHERE clause has an un-parenthesized OR. The legacy regex
    branches treat such clauses as one simple condition and silently match
    nothing, so these queries must go to the SQLite engine."""
    where = re.search(r"\bWHERE\b(.+)$", text, flags=re.I | re.S)
    if not where:
        return False
    return len(_split_sql_top_level(where.group(1), "OR")) > 1


def _sqlite_cell(value: Any) -> Any:
    if isinstance(value, bool):
        # Workato smart-list cells are string-typed; recipes compare
        # active_subscription = 'true', so True must not bind as 1.
        return "true" if value else "false"
    if value is MISSING or value is None or isinstance(value, (int, float, str)):
        return None if value is MISSING else value
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


_SQLITE_KEYWORD_COLUMNS = {
    "group", "order", "index", "limit", "offset", "key", "default", "values",
    "set", "from", "to", "match", "plan", "action", "check", "table", "join",
}


def _single_quote_mask(sql: str) -> list[bool]:
    mask: list[bool] = []
    inside = False
    for char in sql:
        if char == "'":
            mask.append(True)
            inside = not inside
        else:
            mask.append(inside)
    return mask


def _sql_quoted_mask(sql: str) -> list[bool]:
    """Positions inside single-quoted strings OR double-quoted identifiers."""
    mask: list[bool] = []
    quote: str | None = None
    for char in sql:
        if quote:
            mask.append(True)
            if char == quote:
                quote = None
        elif char in {"'", '"'}:
            mask.append(True)
            quote = char
        else:
            mask.append(False)
    return mask


def _quote_reserved_columns(sql: str, columns: set[str]) -> str:
    """Double-quote known list columns whose names are SQLite keywords (e.g. a
    column literally named `group`), outside string literals. `GROUP BY` /
    `ORDER BY` keywords are preserved via the `\\s+BY` lookahead."""
    reserved = sorted(
        {str(col) for col in columns if str(col).lower() in _SQLITE_KEYWORD_COLUMNS},
        key=len,
        reverse=True,
    )
    if not reserved:
        return sql
    out = sql
    for col in reserved:
        pattern = re.compile(
            r'(?<!["\w])' + re.escape(col) + r'(?!["\w])(?!\s+BY\b)', flags=re.I
        )
        # Mask BOTH quote kinds: keyword substrings inside already-quoted
        # list names ("general/group territory...") must not be re-quoted.
        mask = _sql_quoted_mask(out)
        pieces: list[str] = []
        last = 0
        for match in pattern.finditer(out):
            if mask[match.start()]:
                continue
            pieces.append(out[last:match.start()])
            pieces.append(f'"{match.group(0)}"')
            last = match.end()
        pieces.append(out[last:])
        out = "".join(pieces)
    return out


def _quote_spaced_list_names(sql: str, keys: list[str]) -> str:
    """Smart lists created via create_list can carry names with spaces or
    dashes (e.g. 'John Smith - Heatmap Contacts'); raw recipes reference them
    unquoted. Wrap known names in double quotes so SQLite can parse them."""
    out = sql
    for key in sorted(keys, key=len, reverse=True):
        if not re.search(r"[ \-]", key):
            continue
        pattern = re.compile(r"\b(FROM|JOIN|INTO|UPDATE)\s+" + re.escape(key), flags=re.I)
        out = pattern.sub(lambda match: f'{match.group(1)} "{key}"', out)
    return out


def _smart_list_sqlite_query(
    sql: str,
    smart_lists: dict[str, list[dict[str, Any]]],
    table_columns: dict[str, list[str]] | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Evaluate query_list SQL against an in-memory SQLite database loaded with
    the current smart lists. Mutations are written back only for the statement's
    target list, so unrelated lists keep their original (possibly nested) values."""
    conn = sqlite3.connect(":memory:")
    try:
        for key, rows in smart_lists.items():
            columns = list((table_columns or {}).get(key) or [])
            for column in smart_list_row_columns(rows):
                if column not in columns:
                    columns.append(column)
            # Snowflake read-back rows carry dual-case key pairs (UPPER +
            # lower, equal values); keep first-seen so SELECT * and by-index
            # schema mapping stay aligned (SQLite columns are
            # case-insensitive anyway).
            seen_lower: set[str] = set()
            deduped: list[str] = []
            for column in columns:
                if column.lower() in seen_lower:
                    continue
                seen_lower.add(column.lower())
                deduped.append(column)
            columns = deduped
            if not columns:
                continue
            quoted = ", ".join(f'"{column}"' for column in columns)
            conn.execute(f'CREATE TABLE "{key}" ({quoted})')
            placeholders = ", ".join("?" for _ in columns)
            for row in rows:
                conn.execute(
                    f'INSERT INTO "{key}" VALUES ({placeholders})',
                    [_sqlite_cell(field_value(row, column)) for column in columns],
                )
        statement = _quote_spaced_list_names(sql, list(smart_lists))
        all_columns: set[str] = set()
        for key, rows in smart_lists.items():
            all_columns.update((table_columns or {}).get(key) or [])
            all_columns.update(smart_list_row_columns(rows))
        statement = _quote_reserved_columns(statement, all_columns)
        mutation = _SQLITE_MUTATION_RE.match(statement)
        target_key = ""
        if mutation:
            target_key = _smart_list_key(next(group for group in mutation.groups() if group).strip('"'))
        is_create = bool(re.match(r"\s*CREATE\s+TABLE\b", statement, flags=re.I))
        if is_create and target_key:
            # query_list CREATE replaces an existing list of the same name.
            conn.execute(f'DROP TABLE IF EXISTS "{target_key}"')
        if mutation and not is_create and not re.search(r"\bRETURNING\b", statement, flags=re.I):
            statement += " RETURNING *"
        try:
            cursor = conn.execute(statement)
            columns_out = [description[0] for description in cursor.description or []]
            out = [
                {columns_out[index]: row[index] for index in range(len(columns_out))}
                for row in cursor.fetchall()
            ]
        except sqlite3.Error as exc:
            raise NonRecipeError(
                f"unsupported workato_smart_list.query_list SQL: {sql} ({exc})"
            ) from exc
        if mutation and target_key:
            read_back = conn.execute(f'SELECT * FROM "{target_key}"')
            back_columns = [description[0] for description in read_back.description or []]
            smart_lists[target_key] = [
                {back_columns[index]: row[index] for index in range(len(back_columns))}
                for row in read_back.fetchall()
            ]
            if table_columns is not None:
                table_columns[target_key] = back_columns
            if is_create:
                columns_out = back_columns
        return out, columns_out
    finally:
        conn.close()


def _split_sql_top_level(text: str, separator: str) -> list[str]:
    """Split SQL on a separator (a keyword like AND/OR, or a punctuation char
    like ','), ignoring separators inside quotes or parentheses. Keyword
    separators are matched case-insensitively with word boundaries."""
    parts: list[str] = []
    depth = 0
    quote: str | None = None
    idx = 0
    start = 0
    is_word = separator[0].isalpha()
    sep_upper = separator.upper()
    while idx < len(text):
        char = text[idx]
        if quote:
            if char == quote:
                quote = None
            idx += 1
            continue
        if char in {"'", '"'}:
            quote = char
            idx += 1
            continue
        if char == "(":
            depth += 1
            idx += 1
            continue
        if char == ")":
            depth = max(0, depth - 1)
            idx += 1
            continue
        if depth == 0:
            if is_word:
                after = idx + len(separator)
                if (
                    text[idx:after].upper() == sep_upper
                    and (idx == 0 or not (text[idx - 1].isalnum() or text[idx - 1] == "_"))
                    and (after >= len(text) or not (text[after].isalnum() or text[after] == "_"))
                ):
                    parts.append(text[start:idx])
                    idx = after
                    start = idx
                    continue
            elif text.startswith(separator, idx):
                parts.append(text[start:idx])
                idx += len(separator)
                start = idx
                continue
        idx += 1
    parts.append(text[start:])
    return parts


def _smart_list_where_matches(row: dict[str, Any], where: str) -> bool:
    """Evaluate an AND of terms where each term is either a simple condition or
    a parenthesized OR-group of simple/IN conditions."""
    for part in _split_sql_top_level(where, "AND"):
        term = part.strip()
        if not term:
            continue
        if term.startswith("(") and term.endswith(")"):
            or_parts = _split_sql_top_level(term[1:-1], "OR")
            if not any(_smart_list_simple_cond(row, sub.strip()) for sub in or_parts if sub.strip()):
                return False
        elif not _smart_list_simple_cond(row, term):
            return False
    return True


def _smart_list_simple_cond(row: dict[str, Any], cond: str) -> bool:
    in_match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_.]*)\s+IN\s*\((.*)\)", cond, flags=re.I | re.S)
    if in_match:
        allowed = {
            _smart_list_sql_literal(part.strip())
            for part in _split_sql_top_level(in_match.group(2), ",")
            if part.strip()
        }
        actual = field_value(row, in_match.group(1))
        return str(actual if actual is not None else "") in allowed
    simple = re.fullmatch(
        r"([A-Za-z_][A-Za-z0-9_.]*)\s*(>=|<=|<>|!=|=|>|<|LIKE)\s*(.+)",
        cond,
        flags=re.I | re.S,
    )
    if simple:
        field, op, literal = simple.group(1), simple.group(2).upper(), _smart_list_sql_literal(simple.group(3).strip())
        if op in {"!=", "<>"}:
            actual = field_value(row, field)
            return str(actual if actual is not None else "") != str(literal)
        return smart_list_row_matches(row, field, "=" if op == "=" else op, literal)
    raise NonRecipeError(f"unsupported smart_list WHERE condition: {cond}")


def _smart_list_where_conditions(where: str) -> list[tuple[str, str, str]] | None:
    """Parse `a LIKE '%x%' AND b = 'y' ...` into (field, op, literal) triples.
    Returns None if any AND-separated part is not a simple condition (so the
    caller falls through to other SQL forms). The AND split is quote-aware so
    literals containing " and " (e.g. LIKE '%Trinidad and Tobago%') are never
    split apart."""
    parts = _split_outside_quotes(where, r"\s+AND\s+")
    conditions: list[tuple[str, str, str]] = []
    for part in parts:
        m = re.fullmatch(
            r"\s*([A-Za-z_][A-Za-z0-9_.]*)\s*(>=|<=|>|<|=|LIKE)\s*(.+?)\s*",
            part,
            flags=re.I | re.S,
        )
        if not m:
            return None
        conditions.append((m.group(1).strip(), m.group(2).upper(), _smart_list_sql_literal(m.group(3))))
    return conditions


def _split_outside_quotes(text: str, sep_pattern: str) -> list[str]:
    """Split text on a regex separator, ignoring matches inside single/double quotes."""
    parts: list[str] = []
    sep = re.compile(sep_pattern, flags=re.I)
    start = 0
    idx = 0
    quote: str | None = None
    while idx < len(text):
        ch = text[idx]
        if quote:
            if ch == quote:
                quote = None
            idx += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            idx += 1
            continue
        m = sep.match(text, idx)
        if m and m.end() > m.start():
            parts.append(text[start:idx])
            start = m.end()
            idx = m.end()
            continue
        idx += 1
    parts.append(text[start:])
    return parts


def _smart_list_sql_literal(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("'") and text.endswith("'"):
        return text[1:-1].replace("''", "'")
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1].replace('""', '"')
    return text


def smart_list_row_matches(row: dict[str, Any], field: str, op: str, expected: str) -> bool:
    actual = field_value(row, field)
    if actual in (None, MISSING):
        actual = ""
    if op == "LIKE":
        actual_text = str(actual).lower()
        pattern = str(expected).lower()
        chunks = [chunk for chunk in pattern.split("%") if chunk]
        return all(chunk in actual_text for chunk in chunks) if chunks else actual_text == pattern
    if op == "=":
        return str(actual) == str(expected)
    comparison = compare_condition_values(actual, expected)
    if op == ">":
        return comparison > 0
    if op == "<":
        return comparison < 0
    if op == ">=":
        return comparison >= 0
    if op == "<=":
        return comparison <= 0
    raise NonRecipeError(f"unsupported workato_smart_list query operator: {op}")


def smart_list_alias_map(result_schema: list[str], source_columns: list[str]) -> dict[str, str]:
    if not result_schema:
        return {}
    aliases: dict[str, str] = {}
    for alias in result_schema:
        source = smart_list_best_source_column(alias, source_columns)
        aliases[alias] = source
    return aliases


def smart_list_best_source_column(alias: str, source_columns: list[str]) -> str:
    alias_norm = _smart_list_normalized_column(alias)
    for column in source_columns:
        if str(column) == str(alias):
            return column
    for column in source_columns:
        if _smart_list_normalized_column(column) == alias_norm:
            return column
    # Workato's schema-name normalization (validated against committed ground
    # truth, e.g. result column Account_Type reads source column Type):
    alias_tail = alias_norm.replace("account", "")
    matches = [
        column for column in source_columns
        if _smart_list_normalized_column(column) == alias_tail
        or _smart_list_normalized_column(column).endswith(alias_tail)
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise NonRecipeError(
            f"smart list column alias {alias!r} matches multiple source columns {matches}; refusing to guess"
        )
    if alias_norm in {"accountid", "id"}:
        for column in source_columns:
            if _smart_list_normalized_column(column) == "id":
                return column
    # Positional alignment: a lone result column maps to the lone source column.
    if len(source_columns) == 1:
        return source_columns[0]
    if not source_columns:
        # Zero-row source list: there is nothing to map; keep the alias as a
        # deterministic no-op (there are no rows for it to select from).
        return alias
    raise NonRecipeError(
        f"smart list column alias {alias!r} does not match any source column {source_columns}; refusing to guess"
    )


def _smart_list_normalized_column(value: str) -> str:
    text = re.sub(r"__c$", "", str(value), flags=re.I)
    return re.sub(r"[^a-z0-9]", "", text.lower())


def smart_list_project_rows(
    rows: list[dict[str, Any]],
    result_schema: list[str],
    alias_map: dict[str, str],
) -> list[dict[str, Any]]:
    if not result_schema:
        return [dict(row) for row in rows]
    projected: list[dict[str, Any]] = []
    for row in rows:
        out = dict(row)
        for alias in result_schema:
            source = alias_map.get(alias, alias)
            out[alias] = field_value(row, source)
        projected.append(out)
    return projected


def slack_text(
    raw_input: dict[str, Any],
    ctx: RecipeContext,
    state: RuntimeState,
    *,
    allow_empty: bool = False,
) -> str:
    message = raw_input.get("message") if isinstance(raw_input.get("message"), dict) else {}
    lines: list[str] = []
    for block in raw_input.get("blocks") or []:
        if isinstance(block, dict):
            lines.extend(slack_block_lines(block, ctx, state))
    top_text = resolve_value(raw_input.get("text"), ctx, state)
    if top_text not in (None, ""):
        lines.append(ruby_to_s(top_text))
    for key in ("pretext", "title", "attachment_text", "text"):
        value = resolve_value(message.get(key), ctx, state)
        if value not in (None, ""):
            lines.append(ruby_to_s(value))
    # Some raw recipes carry pretext/title/attachment_text at the input top
    # level instead of nested under "message" (e.g. post_message_to_channel).
    # Render those too; skip "text" (already handled above as top_text).
    for key in ("pretext", "title", "attachment_text"):
        if key in message:
            continue
        value = resolve_value(raw_input.get(key), ctx, state)
        if value not in (None, "", MISSING):
            lines.append(ruby_to_s(value))
    raw_fields = raw_input.get("attachment_fields")
    if isinstance(raw_fields, dict) and "____source" in raw_fields:
        # Source-mapped field list: one rendered field per source row.
        raw_fields = resolve_source_mapping(raw_fields, ctx, state)
    for field in raw_fields or []:
        if not isinstance(field, dict):
            continue
        # Nil parity: an absent pill renders "", never the MISSING sentinel.
        title = resolve_value(field.get("title"), ctx, state)
        value = resolve_value(field.get("value"), ctx, state)
        title = "" if title is MISSING else title
        value = "" if value is MISSING else value
        if title not in (None, "") or value not in (None, ""):
            lines.append(f"{ruby_to_s(title)}: {ruby_to_s(value)}")
    text = "\n".join(lines)
    if not text and not allow_empty:
        raise RawRecipeExecutionError("Slack message rendered empty text")
    # ``<anon>`` wrappers are dataset metadata, not user-visible Slack markup.
    # They may wrap a substring inside a larger configured template, so the
    # whole-value-only helper used for comparisons is insufficient here.
    return re.sub(r"<anon>(.*?)</anon>", r"\1", text, flags=re.DOTALL)


def slack_attachments(
    raw_input: dict[str, Any],
    ctx: RecipeContext,
    state: RuntimeState,
) -> list[dict[str, Any]]:
    """Project Workato's legacy Slack attachment fields to the public API."""

    message = raw_input.get("message") if isinstance(raw_input.get("message"), dict) else {}
    attachment: dict[str, Any] = {}
    for public_key, source_key in (
        ("color", "color"),
        ("pretext", "pretext"),
        ("title", "title"),
        ("title_link", "title_link"),
        ("text", "attachment_text"),
        ("footer", "footer"),
        ("footer_icon", "footer_icon"),
    ):
        configured = (
            message[source_key]
            if source_key in message
            else raw_input.get(source_key, MISSING)
        )
        value = resolve_value(configured, ctx, state)
        if value in (None, "", MISSING):
            continue
        attachment[public_key] = re.sub(
            r"<anon>(.*?)</anon>",
            r"\1",
            ruby_to_s(value),
            flags=re.DOTALL,
        )

    raw_fields = raw_input.get("attachment_fields")
    if isinstance(raw_fields, dict) and "____source" in raw_fields:
        raw_fields = resolve_source_mapping(raw_fields, ctx, state)
    fields: list[dict[str, Any]] = []
    for field in raw_fields or []:
        if not isinstance(field, dict):
            continue
        title = resolve_value(field.get("title"), ctx, state)
        value = resolve_value(field.get("value"), ctx, state)
        title = "" if title in (None, MISSING) else ruby_to_s(title)
        value = "" if value in (None, MISSING) else ruby_to_s(value)
        if not title and not value:
            continue
        projected = {"title": title, "value": value}
        if "short" in field:
            projected["short"] = truthy(resolve_value(field.get("short"), ctx, state))
        fields.append(projected)
    if fields:
        attachment["fields"] = fields

    raw_actions = raw_input.get("attachment_buttons")
    actions: list[dict[str, Any]] = []
    for action in raw_actions or []:
        if not isinstance(action, dict):
            continue
        projected = {
            str(key): resolve_value(value, ctx, state)
            for key, value in action.items()
            if value not in (None, "")
        }
        if projected:
            actions.append(projected)
    if actions:
        attachment["actions"] = actions

    return [attachment] if attachment else []


def slack_block_lines(block: dict[str, Any], ctx: RecipeContext, state: RuntimeState) -> list[str]:
    lines: list[str] = []
    if block.get("section_text"):
        value = resolve_value(block.get("section_text"), ctx, state)
        if value not in (None, ""):
            lines.append(ruby_to_s(value))
    for element in block.get("elements") or []:
        if not isinstance(element, dict):
            continue
        value = resolve_value(element.get("text"), ctx, state)
        if value not in (None, ""):
            lines.append(ruby_to_s(value))
    objects = block.get("objects")
    if isinstance(objects, dict):
        if "____source" in objects:
            # repeat_block_group: the objects mapping itself carries the
            # source — the inner section repeats once per source row. Each
            # resolved wrapper keeps the template shape ({"blocks": [...]}),
            # so descend into the wrapper AND its "blocks" children; the
            # non-source fall-through below must NOT also run (it would
            # render the inner section one extra time against ambient ctx).
            for resolved in resolve_source_mapping(objects, ctx, state):
                lines.extend(slack_block_lines(resolved, ctx, state))
                wrapper_blocks = resolved.get("blocks")
                if isinstance(wrapper_blocks, list):
                    for child in wrapper_blocks:
                        if isinstance(child, dict):
                            lines.extend(slack_block_lines(child, ctx, state))
        else:
            child_blocks = objects.get("blocks")
            if isinstance(child_blocks, dict):
                for resolved in resolve_source_mapping(child_blocks, ctx, state):
                    lines.extend(slack_block_lines(resolved, ctx, state))
            elif isinstance(child_blocks, list):
                for child in child_blocks:
                    if isinstance(child, dict):
                        if "____source" in child:
                            for resolved in resolve_source_mapping(child, ctx, state):
                                lines.extend(slack_block_lines(resolved, ctx, state))
                        else:
                            lines.extend(slack_block_lines(child, ctx, state))
    return lines


_DP_RE = re.compile(r"#\{_dp\('([^']+)'\)\}")
# Same as _DP_RE but also captures an optional trailing Ruby method chain
# (e.g. #{_dp('...').gsub("_"," ").titleize}); group(2) is "" when absent.
_DP_CHAIN_RE = re.compile(r"#\{_dp\('([^']+)'\)((?:\.[A-Za-z_][A-Za-z0-9_?!]*(?:\([^()]*\))?)*)\}")
_DP_CALL_RE = re.compile(r"_dp\('([^']+)'\)")
_DATA_CALL_RE = re.compile(r"_\('([^']+)'\)")


def resolve_value(value: Any, ctx: RecipeContext, state: RuntimeState) -> Any:
    if isinstance(value, dict):
        if "____source" in value:
            return resolve_source_mapping(value, ctx, state)
        out: dict[Any, Any] = {}
        for key, raw in value.items():
            resolved = resolve_value(raw, ctx, state)
            if resolved is SKIP:
                continue
            out[key] = None if resolved is MISSING else resolved
        return out
    if isinstance(value, list):
        out: list[Any] = []
        for item in value:
            resolved = resolve_value(item, ctx, state)
            if resolved is SKIP:
                continue
            out.append(None if resolved is MISSING else resolved)
        return out
    if not isinstance(value, str):
        return value
    if value.startswith("="):
        return eval_formula(value, ctx, state)
    if not _DP_RE.search(value):
        return value
    whole = _DP_RE.fullmatch(value)
    if whole:
        return resolve_dp_json(whole.group(1), ctx, state)
    return _DP_RE.sub(lambda match: ruby_to_s(resolve_dp_json(match.group(1), ctx, state)), value)


def resolve_text(value: Any, ctx: RecipeContext, state: RuntimeState) -> str:
    """Adapter-boundary string rendering with Workato/Ruby falsy parity: an
    absent/nil pill renders "" (like interpolation) while 0/false/[] render
    their Ruby to_s forms ('0'/'false'/'[]'), never '' (same normative
    matrix as ruby_to_s)."""
    return ruby_to_s(resolve_value(value, ctx, state))


def interpolate_literal_text(value: str, ctx: RecipeContext, state: RuntimeState) -> str:
    def _pill(match: "re.Match[str]") -> str:
        v = resolve_dp_json(match.group(1), ctx, state)
        chain = match.group(2)
        if chain and v is not MISSING:
            v = apply_dp_methods(v, chain, ctx, state)
        return ruby_to_s(v)

    # Ruby double-quoted semantics: literal segments decode escape sequences
    # (\n, \t, \"); pill VALUES are substituted verbatim.
    out: list[str] = []
    last = 0
    for match in _DP_CHAIN_RE.finditer(value):
        out.append(decode_workato_string(value[last:match.start()]))
        out.append(_pill(match))
        last = match.end()
    out.append(decode_workato_string(value[last:]))
    return "".join(out)


def interpolate_formula_string(value: str, ctx: RecipeContext, state: RuntimeState) -> str | None:
    """Render every #{...} segment of a formula string literal by evaluating the
    inner expression (datapill, data-call, or formula fragment). Brace matching
    is quote-aware so JSON pill payloads inside _dp('...') survive. Returns None
    when a bare double quote appears outside an interpolation — the text is then
    not a single string literal (e.g. `"a" + "b"`), and the caller must fall
    through to its other formula forms."""
    out: list[str] = []
    i = 0
    while True:
        start = value.find("#{", i)
        if start == -1:
            tail = value[i:]
            if '"' in tail:
                return None
            # Ruby double-quoted semantics: literal segments decode escape
            # sequences (\n, \t) — pill VALUES are appended verbatim below.
            out.append(decode_workato_string(tail))
            return "".join(out)
        head = value[i:start]
        if '"' in head:
            return None
        out.append(decode_workato_string(head))
        j = start + 2
        depth = 1
        quote: str | None = None
        # Stack of (depth_at_open, saved_quote) for interpolations that open
        # INSIDE a quoted segment (e.g. `#{a > 0 ? (",#{b}") : ""}`) — Ruby
        # nests a fresh lexing context there, so the scanner must too.
        nested: list[tuple[int, str]] = []
        while j < len(value):
            ch = value[j]
            if quote:
                if ch == "\\":
                    j += 2
                    continue
                if quote == '"' and value.startswith("#{", j):
                    nested.append((depth + 1, quote))
                    quote = None
                    depth += 1
                    j += 2
                    continue
                if ch == quote:
                    quote = None
            elif ch in "'\"":
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
                if nested and nested[-1][0] == depth + 1:
                    quote = nested.pop()[1]
            j += 1
        if depth != 0:
            raise NonRecipeError(f"unterminated interpolation in formula literal: {value}")
        rendered = eval_formula("=" + value[start + 2:j], ctx, state)
        out.append(ruby_to_s(rendered))
        i = j + 1


def resolve_source_mapping(raw_mapping: dict[str, Any], ctx: RecipeContext, state: RuntimeState) -> list[dict[Any, Any]]:
    raw_source = raw_mapping.get("____source")
    source = resolve_value(raw_source, ctx, state)
    items = as_list(source)
    template = {key: value for key, value in raw_mapping.items() if key != "____source"}
    info = source_datapill_info(raw_source)
    out: list[dict[Any, Any]] = []
    for item in items:
        with_source_current_item(state, info, item)
        try:
            resolved = resolve_value(template, ctx, state)
        finally:
            restore_source_current_item(state, info)
        if not isinstance(resolved, dict):
            raise RawRecipeExecutionError("source mapping item did not resolve to an object")
        out.append(resolved)
    return out


def source_datapill_info(raw_source: Any) -> dict[str, Any]:
    if not isinstance(raw_source, str):
        return {}
    match = _DP_RE.fullmatch(raw_source)
    if not match:
        return {}
    try:
        pill = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
    path = pill.get("path") if isinstance(pill.get("path"), list) else []
    # Collection path = the source pill path. Usually a single key
    # (e.g. ["rows"]); nested sources like ["request", "entries"] and
    # NESTED-LOOP sources like ["outer", {current_item}, "inner"] are valid
    # Workato mappings too — truncating at the current_item hop used to
    # rebind the OUTER collection to the inner item (silent nulls).
    collection_path: list[Any] = []
    for element in path:
        if isinstance(element, str):
            collection_path.append(str(element))
        elif isinstance(element, dict) and element.get("path_element_type") == "current_item":
            collection_path.append({"path_element_type": "current_item"})
        else:
            break
    while collection_path and not isinstance(collection_path[-1], str):
        collection_path.pop()
    collection_key = collection_path[0] if collection_path and isinstance(collection_path[0], str) else ""
    return {
        "line": str(pill.get("line") or ""),
        "provider": str(pill.get("provider") or ""),
        "collection_key": collection_key,
        "collection_path": collection_path,
        "_original_step": MISSING,
        "_original_provider": MISSING,
    }


def with_source_current_item(state: RuntimeState, info: dict[str, Any], item: Any) -> None:
    line = str(info.get("line") or "")
    collection_path = info.get("collection_path") or ([info["collection_key"]] if info.get("collection_key") else [])
    if not line or not collection_path:
        return
    provider = str(info.get("provider") or "")
    info["_original_step"] = state.steps.get(line, MISSING)
    provider_data = state.data.get(provider, {}) if provider else {}
    info["_original_provider"] = provider_data.get(line, MISSING)
    current_step = info["_original_step"]
    if isinstance(current_step, dict):
        state.steps[line] = _patch_nested_collection(current_step, collection_path, item)
    if provider:
        state.data.setdefault(provider, {})
        current_provider = info["_original_provider"]
        if isinstance(current_provider, dict):
            state.data[provider][line] = _patch_nested_collection(current_provider, collection_path, item)


def _patch_nested_collection(container: dict[str, Any], keys: list[Any], item: Any) -> dict[str, Any]:
    """Shallow-copy container along keys and set the final key to [item].
    A current_item hop descends into the head of the (already single-item)
    list an ENCLOSING source loop patched — so a nested source path like
    ["outer", {current_item}, "inner"] patches outer[0]["inner"], never the
    outer collection itself."""
    patched = dict(container)
    node: dict[str, Any] = patched
    idx = 0
    while idx < len(keys) - 1:
        key = keys[idx]
        if not isinstance(key, str):
            raise RawRecipeExecutionError(f"unsupported source collection path: {keys!r}")
        if idx + 1 < len(keys) - 1 and not isinstance(keys[idx + 1], str):
            entries = node.get(key)
            entries = list(entries) if isinstance(entries, list) else []
            head = dict(entries[0]) if entries and isinstance(entries[0], dict) else {}
            if entries:
                entries[0] = head
            else:
                entries = [head]
            node[key] = entries
            node = head
            idx += 2
            continue
        child = node.get(key)
        child = dict(child) if isinstance(child, dict) else {}
        node[key] = child
        node = child
        idx += 1
    last = keys[-1]
    if not isinstance(last, str):
        raise RawRecipeExecutionError(f"source collection path must end in a key: {keys!r}")
    node[last] = [item]
    return patched


def restore_source_current_item(state: RuntimeState, info: dict[str, Any]) -> None:
    line = str(info.get("line") or "")
    if not line:
        return
    provider = str(info.get("provider") or "")
    original_step = info.get("_original_step", MISSING)
    if original_step is MISSING:
        state.steps.pop(line, None)
    else:
        state.steps[line] = original_step
    if provider:
        original_provider = info.get("_original_provider", MISSING)
        if original_provider is MISSING:
            state.data.get(provider, {}).pop(line, None)
        else:
            state.data.setdefault(provider, {})[line] = original_provider


def resolve_dp_json(raw: str, ctx: RecipeContext, state: RuntimeState) -> Any:
    try:
        pill = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RawRecipeExecutionError(f"invalid datapill JSON: {raw}") from exc
    pill_type = pill.get("pill_type")
    if pill_type == "account_property":
        name = str(pill.get("property_name") or "")
        values = ctx.seed.get("account_properties") if isinstance(ctx.seed.get("account_properties"), dict) else {}
        if name in values:
            return values[name]
        # Live-isolation affordance: unseeded slack-channel account properties
        # resolve to the benchmark override channel so recipes never post to a
        # real org channel. Explicitly seeded values always win (above).
        if "slack" in name.lower() and "channel" in name.lower() and ctx.env.slack_channel_override:
            return ctx.env.slack_channel_override
        raise RawRecipeExecutionError(f"missing account property datapill: {name}")
    if pill_type == "project_property":
        name = str(pill.get("property_name") or "")
        values = ctx.seed.get("project_properties") if isinstance(ctx.seed.get("project_properties"), dict) else {}
        if name not in values:
            raise RawRecipeExecutionError(f"missing project property datapill: {name}")
        return values[name]
    if pill_type == "output":
        line = str(pill.get("line") or "")
        root = state.steps.get(line, MISSING)
        if root is MISSING:
            root = state.data.get(str(pill.get("provider") or ""), {}).get(line, MISSING)
        path = pill.get("path") or []
        value = lookup_path(root, path)
        if (
            value is MISSING
            and str(pill.get("provider") or "") == "foreach"
            and len(path) == 1
            and str(path[0]) in {"index", "seq_no", "size"}
        ):
            # Loop counters live in foreach_meta, not on the current item —
            # mirrors the _('data.foreach.<line>.seq_no') fallback in data_path.
            meta = state.foreach_meta.get(line)
            if isinstance(meta, dict) and str(path[0]) in meta:
                return meta[str(path[0])]
        return value
    if pill_type == "job_context":
        root = ctx.seed.get("job_context") if isinstance(ctx.seed.get("job_context"), dict) else {}
        return lookup_path(root, pill.get("path") or [])
    if pill_type == "foreach_meta":
        line = str(pill.get("line") or "")
        meta = state.foreach_meta.get(line)
        if not isinstance(meta, dict):
            raise RawRecipeExecutionError(f"foreach_meta datapill outside an active foreach: line {line}")
        key = str(pill.get("key") or "")
        if not key:
            path = pill.get("path") or []
            key = str(path[0]) if path else ""
        if key not in meta:
            raise RawRecipeExecutionError(f"unknown foreach_meta key {key!r} for line {line}")
        return meta[key]
    raise NonRecipeError(f"unsupported datapill type: {pill_type}")


def eval_formula(expr: str, ctx: RecipeContext, state: RuntimeState) -> Any:
    # Run the existing regex dispatch first; only when it cannot handle the
    # formula (raises) do we fall back to the general arithmetic engine, so no
    # currently-supported form changes behavior.
    try:
        return _eval_formula_impl(expr, ctx, state)
    except (RawRecipeExecutionError, NonRecipeError):
        text = strip_formula_comment(expr[1:].strip())
        result = _eval_arith_formula(text, ctx, state)
        if result is _ARITH_NOMATCH:
            raise
        return result
    except _ArithNoMatch:
        # A regex-dispatch branch mis-split an expression it cannot actually
        # handle (e.g. a top-level '-' inside a bracket index) and leaked the
        # parser sentinel — give the full arithmetic engine one shot.
        text = strip_formula_comment(expr[1:].strip())
        result = _eval_arith_formula(text, ctx, state)
        if result is _ARITH_NOMATCH:
            raise NonRecipeError(f"unsupported formula: {expr}")
        return result


def _eval_formula_impl(expr: str, ctx: RecipeContext, state: RuntimeState) -> Any:
    text = strip_formula_comment(expr[1:].strip())

    if text == "":
        return ""
    if text == "nil":
        return None
    if text == "blank":
        # Workato formula-mode 'blank' literal — nil (production-verified on
        # 121126518 v7; used in else-branches to leave a variable unset).
        return None
    if text == "workato.uuid":
        # Deterministic uuids: seeded list consumed in call order (a random
        # uuid could never be pinned as groundtruth).
        uuids = ctx.seed.get("workato_uuids")
        if not isinstance(uuids, list) or not uuids:
            raise RawRecipeExecutionError(
                "=workato.uuid requires seed.workato_uuids (a deterministic list consumed in call order)"
            )
        if state.workato_uuid_index >= len(uuids):
            raise RawRecipeExecutionError(
                f"=workato.uuid call #{state.workato_uuid_index + 1} exceeds the "
                f"{len(uuids)} seeded workato_uuids"
            )
        value = str(uuids[state.workato_uuid_index])
        state.workato_uuid_index += 1
        return value
    if text == "null":
        return None
    if text == "true":
        return True
    if text == "false":
        return False
    if text == "skip":
        return SKIP
    if text == "clear":
        return ""
    numeric_literal = re.fullmatch(r"-?\d+(?:\.\d+)?", text)
    if numeric_literal:
        return Decimal(text) if "." in text else int(text)
    if text in {"now", "now()"}:
        if "now" not in ctx.seed or ctx.seed.get("now") in (None, ""):
            raise RawRecipeExecutionError("formula 'now' requires a fixed seed['now']")
        return ctx.seed["now"]
    now_plus = re.fullmatch(r"now\s*\+\s*(\d+)\.(weeks?|years?)", text)
    if now_plus:
        if "now" not in ctx.seed or ctx.seed.get("now") in (None, ""):
            raise RawRecipeExecutionError("formula 'now' requires a fixed seed['now']")
        dt = datetime.datetime.fromisoformat(str(ctx.seed["now"]).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise RawRecipeExecutionError("formula 'now' requires seed['now'] to include timezone information")
        amount = int(now_plus.group(1))
        unit = now_plus.group(2)
        if unit.startswith("week"):
            return (dt + datetime.timedelta(weeks=amount)).astimezone(datetime.timezone.utc).isoformat()
        return shift_months(dt, amount * 12).astimezone(datetime.timezone.utc).isoformat()
    now_minus_months = re.fullmatch(r"now\s*-\s*(\d+)\.months", text)
    if now_minus_months:
        if "now" not in ctx.seed or ctx.seed.get("now") in (None, ""):
            raise RawRecipeExecutionError("formula 'now' requires a fixed seed['now']")
        dt = datetime.datetime.fromisoformat(str(ctx.seed["now"]).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise RawRecipeExecutionError("formula 'now' requires seed['now'] to include timezone information")
        return shift_months(dt, -int(now_minus_months.group(1))).astimezone(datetime.timezone.utc).isoformat()
    now_hours = re.fullmatch(r"now\s*([+-])\s*(\d+)\.hours?", text)
    if now_hours:
        dt = _seed_now_dt(ctx)
        delta = datetime.timedelta(hours=int(now_hours.group(2)))
        dt = dt + delta if now_hours.group(1) == "+" else dt - delta
        return dt.astimezone(datetime.timezone.utc).isoformat()
    paren_now_hours_to_i = re.fullmatch(r"\(\s*now\s*([+-])\s*(\d+)\.hours?\s*\)\.to_i", text)
    if paren_now_hours_to_i:
        dt = _seed_now_dt(ctx)
        delta = datetime.timedelta(hours=int(paren_now_hours_to_i.group(2)))
        dt = dt + delta if paren_now_hours_to_i.group(1) == "+" else dt - delta
        return int(dt.timestamp())
    now_to_date_epoch = re.fullmatch(
        r"\(\s*now\s*\)\.to_date\.to_time\.to_i(?:\s*([+-])\s*(\d+))?",
        text,
    )
    if now_to_date_epoch:
        dt = _seed_now_dt(ctx)
        midnight = datetime.datetime.combine(dt.date(), datetime.time(), tzinfo=dt.tzinfo)
        epoch = int(midnight.timestamp())
        if now_to_date_epoch.group(1):
            amount = int(now_to_date_epoch.group(2))
            epoch = epoch + amount if now_to_date_epoch.group(1) == "+" else epoch - amount
        return epoch
    now_minus_minutes = re.fullmatch(
        r"now\s*-\s*_dp\('([^']+)'\)\.to_i\.minutes",
        text,
        flags=re.S,
    )
    if now_minus_minutes:
        if "now" not in ctx.seed or ctx.seed.get("now") in (None, ""):
            raise RawRecipeExecutionError("formula 'now' requires a fixed seed['now']")
        minutes_value = resolve_dp_json(now_minus_minutes.group(1), ctx, state)
        match = re.search(r"-?\d+", str(minutes_value or ""))
        minutes = int(match.group(0)) if match else 0
        dt = datetime.datetime.fromisoformat(str(ctx.seed["now"]).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise RawRecipeExecutionError("formula 'now' requires seed['now'] to include timezone information")
        return (dt - datetime.timedelta(minutes=minutes)).astimezone(datetime.timezone.utc).isoformat()
    epoch_timezone = re.fullmatch(
        r"\(\s*'1970-01-01'\.to_time\s*\+\s*_dp\('([^']+)'\)\.seconds\s*\)\.in_time_zone\(_dp\('([^']+)'\)\)",
        text,
        flags=re.S,
    )
    if epoch_timezone:
        seconds = resolve_dp_json(epoch_timezone.group(1), ctx, state)
        timezone_name = resolve_dp_json(epoch_timezone.group(2), ctx, state)
        return epoch_seconds_in_timezone(seconds, timezone_name)
    if text == "today.wday":
        return seed_today(ctx).isoweekday() % 7
    if text in {"today", "today()"}:
        return seed_today(ctx).isoformat()
    ago_value = _eval_ago_expr(text, ctx)
    if ago_value is not _ARITH_NOMATCH:
        return ago_value
    today_minus = re.fullmatch(r"today\s*-\s*(\d+)\.(days?|months?)", text)
    if today_minus:
        amount = int(today_minus.group(1))
        unit = today_minus.group(2)
        base_date = seed_today(ctx)
        if unit.startswith("day"):
            return (base_date - datetime.timedelta(days=amount)).isoformat()
        base_dt = datetime.datetime.combine(base_date, datetime.time(), tzinfo=datetime.timezone.utc)
        return shift_months(base_dt, -amount).date().isoformat()
    today_strftime_to_i = re.fullmatch(r'today\.strftime\("((?:\\.|[^"])*)"\)\.to_i', text, flags=re.S)
    if today_strftime_to_i:
        rendered = render_strftime(
            datetime.datetime.combine(seed_today(ctx), datetime.time(), tzinfo=datetime.timezone.utc),
            decode_workato_string(today_strftime_to_i.group(1)),
        )
        match = re.search(r"-?\d+", rendered)
        return int(match.group(0)) if match else 0
    today_strftime = re.fullmatch(r'today\.strftime\("((?:\\.|[^"])*)"\)', text, flags=re.S)
    if today_strftime:
        return render_strftime(
            datetime.datetime.combine(seed_today(ctx), datetime.time(), tzinfo=datetime.timezone.utc),
            decode_workato_string(today_strftime.group(1)),
        )
    if text.endswith(".presence or skip"):
        value = eval_formula("=" + text[: -len(".presence or skip")], ctx, state)
        return value if present(value) else SKIP

    presence_pair = split_presence_or(text)
    if presence_pair:
        left, right = presence_pair
        left_value = eval_formula("=" + left, ctx, state)
        return left_value if present(left_value) else eval_formula("=" + right, ctx, state)

    if text.endswith(".presence"):
        value = eval_formula("=" + text[: -len(".presence")], ctx, state)
        # Rails parity: `.presence` of a blank yields nil (None), never "".
        # A nil then renders "" in string contexts but is OMITTED at optional
        # connector-input boundaries (the Salesforce write handlers'
        # nil-compaction).
        return value if present(value) else None

    if re.match(r"\(?\s*lookup\s*\(", text):
        return eval_lookup_expr(text, ctx, state)

    if text.startswith("if "):
        return eval_if_formula(text, ctx, state)

    if text.startswith("[") and text.endswith("]"):
        return eval_dp_formula(text, ctx, state)

    if text.startswith("{"):
        return eval_dp_formula(text, ctx, state)

    if "_dp(" in text:
        return eval_dp_formula(text, ctx, state)

    plus_days = re.fullmatch(r"_\('([^']+)'\)\s*\+\s*(\d+)\.days", text)
    if plus_days:
        value = data_path(plus_days.group(1), state)
        return plus_days_to_date(value, int(plus_days.group(2)))

    present_include = re.fullmatch(
        r"_\('([^']+)'\)\.present\?\s*&&\s*_\('([^']+)'\)\.include\?\(\"([^\"]*)\"\)",
        text,
        flags=re.S,
    )
    if present_include:
        left = data_path(present_include.group(1), state)
        right = data_path(present_include.group(2), state)
        return present(left) and present_include.group(3) in str(right)

    strftime = re.fullmatch(r"_\('([^']+)'\)\.strftime\(\"([^\"]*)\"\)", text, flags=re.S)
    if strftime:
        return strftime_workato(data_path(strftime.group(1), state), strftime.group(2))

    seeded_now_strftime = re.fullmatch(
        r"now\.in_time_zone\((['\"])(.*?)\1\)\.strftime\((['\"])(.*?)\3\)",
        text,
        flags=re.S,
    )
    if seeded_now_strftime:
        return strftime_seed_now_in_zone(ctx, seeded_now_strftime.group(2), seeded_now_strftime.group(4))

    ternary = re.fullmatch(
        r"_\('([^']+)'\)\.is_true\?\s*\?\s*\"([^\"]*)\"\s*:\s*\"([^\"]*)\"",
        text,
        flags=re.S,
    )
    if ternary:
        return ternary.group(2) if truthy(data_path(ternary.group(1), state)) else ternary.group(3)

    pluck_sum = re.fullmatch(r"_\('([^']+)'\)\.pluck\('([^']+)'\)\.compact\.sum", text)
    if pluck_sum:
        rows = data_path(pluck_sum.group(1), state)
        return decimal_sum([field_value(row, pluck_sum.group(2)) for row in as_list(rows)])

    # Inline ternary, e.g. _('path').present? ? _('path') : skip . The condition
    # and both branches are evaluated as sub-formulas so this composes with the
    # data-call/skip/nil handling. Placed after the specific is_true? ternary so
    # existing behavior is unchanged.
    ternary_parts = split_top_level_ternary(text)
    if ternary_parts:
        condition, truth_value, false_value = ternary_parts
        condition_result = eval_formula("=" + condition, ctx, state)
        branch = truth_value if formula_condition(condition_result) else false_value
        return eval_formula("=" + branch, ctx, state)

    # Ruby date-range count, e.g. (_('...CreatedDate').to_date...today).count —
    # the number of days in the range (exclusive for ..., inclusive for ..).
    range_count = re.fullmatch(r"\((.+?)(\.\.\.|\.\.)(.+?)\)\.count", text, flags=re.S)
    if range_count:
        start_val = _arith_to_datetime(eval_formula("=" + range_count.group(1).strip(), ctx, state))
        end_val = _arith_to_datetime(eval_formula("=" + range_count.group(3).strip(), ctx, state))
        if start_val is None or end_val is None:
            raise RawRecipeExecutionError(f"date-range count on non-date operands: {text}")
        days = (end_val.date() - start_val.date()).days
        if range_count.group(2) == "..":
            days += 1
        return max(days, 0)

    # Data-call with an explicit source kind, e.g.
    # _('data.foreach.<line>.index', 'foreach_meta') (0-based loop index) or the
    # list_meta fallback form _('...list.first.____Size', 'list_meta', ...).
    if text.startswith("_('"):
        or_idx = find_top_level_token(text, " or ")
        if or_idx != -1 and not text[:or_idx].rstrip().endswith(".presence"):
            # Ruby value `or`: return the left operand unless it is nil/false
            # ("" and 0 are TRUTHY in Ruby). Whole-text chain dispatch used to
            # swallow the split and apply the right side's methods to the kept
            # left value (85944334 class — silent MISSING when left truthy).
            # `.presence or` keeps its blank-falls-through path below.
            left = eval_formula("=" + text[:or_idx].strip(), ctx, state)
            if left is not MISSING and left is not None and left is not False:
                return left
            return eval_formula("=" + text[or_idx + 4:].strip(), ctx, state)

    data_call_meta = re.fullmatch(
        r"_\('([^']+)'\s*,\s*'([^']*)'(?:\s*,\s*'[^']*')*\)(.*)",
        text,
        flags=re.S,
    )
    if data_call_meta:
        value = resolve_data_call(data_call_meta.group(1), data_call_meta.group(2), state)
        return apply_dp_methods(value, data_call_meta.group(3), ctx, state)

    data_call_methods = re.fullmatch(r"_\('([^']+)'\)(.*)", text, flags=re.S)
    if data_call_methods:
        return apply_dp_methods(data_path(data_call_methods.group(1), state), data_call_methods.group(2), ctx, state)

    call = re.fullmatch(r"_\('([^']+)'\)", text)
    if call:
        return data_path(call.group(1), state)

    if len(text) >= 2 and text.startswith('"') and text.endswith('"') and "#{" in text:
        # Interpolated string literal, e.g. ="R#{(_('...').to_i) + 1}". The
        # helper returns None when a bare quote sits outside #{...} (the text is
        # then a concat/comparison, not one literal) — fall through in that case.
        rendered = interpolate_formula_string(text[1:-1], ctx, state)
        if rendered is not None:
            return rendered

    literal = re.fullmatch(r"\"([^\"]*)\"", text, flags=re.S)
    if literal:
        return literal.group(1)

    if text.startswith("["):
        # Pill-less array literal with a method chain, e.g. =["a","b"].join(",").
        # (The pill-bearing form routes through eval_dp_formula.)
        close = matching_bracket_index(text)
        chain = text[close + 1:].strip() if close != -1 else ""
        if close != -1 and chain.startswith((".", "&.")):
            inner = text[1:close].strip()
            elements = (
                [eval_dp_formula(part, ctx, state) for part in split_top_level(inner, ",")]
                if inner
                else []
            )
            return apply_dp_methods(elements, chain, ctx, state)

    raise NonRecipeError(f"unsupported formula: {expr}")


def eval_dp_formula(text: str, ctx: RecipeContext, state: RuntimeState) -> Any:
    try:
        return _eval_dp_formula_impl(text, ctx, state)
    except RawRecipeExecutionError:
        stripped = strip_wrapping_parens(strip_formula_comment(text.strip()))
        result = _eval_arith_formula(stripped, ctx, state)
        if result is _ARITH_NOMATCH:
            raise
        return result


def _eval_dp_formula_impl(text: str, ctx: RecipeContext, state: RuntimeState) -> Any:
    text = strip_wrapping_parens(strip_formula_comment(text.strip()))

    # Ruby date-range count on datapill operands, e.g.
    # (_dp('...CreatedDate').to_date...today).count — same handler as
    # _eval_formula_impl; operands evaluate through the full formula engine.
    range_count = re.fullmatch(r"\((.+?)(\.\.\.|\.\.)(.+?)\)\.count", text, flags=re.S)
    if range_count:
        start_val = _arith_to_datetime(eval_formula("=" + range_count.group(1).strip(), ctx, state))
        end_val = _arith_to_datetime(eval_formula("=" + range_count.group(3).strip(), ctx, state))
        if start_val is None or end_val is None:
            raise RawRecipeExecutionError(f"date-range count on non-date operands: {text}")
        days = (end_val.date() - start_val.date()).days
        if range_count.group(2) == "..":
            days += 1
        return max(days, 0)

    if text == "nil":
        return None
    if text == "null":
        return None
    if text == "true":
        return True
    if text == "false":
        return False
    if text == "skip":
        return SKIP
    if text == "clear":
        return ""

    if _HASH_LITERAL_RE.match(text):
        hash_value, remainder = _parse_hash_literal(text, ctx, state)
        if not remainder:
            return hash_value
        return apply_dp_methods(hash_value, remainder, ctx, state)

    ago_value = _eval_ago_expr(text, ctx)
    if ago_value is not _ARITH_NOMATCH:
        return ago_value

    if re.match(r"\(?\s*lookup\s*\(", text):
        return eval_lookup_expr(text, ctx, state)

    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [eval_dp_formula(part, ctx, state) for part in split_top_level(inner, ",")]

    ternary = split_top_level_ternary(text)
    if ternary:
        condition, truth_value, false_value = ternary
        condition_value = eval_dp_formula(condition, ctx, state)
        return eval_dp_formula(truth_value, ctx, state) if formula_condition(condition_value) else eval_dp_formula(false_value, ctx, state)

    parts = split_top_level(text, "||")
    if len(parts) > 1:
        left = eval_dp_formula(parts[0], ctx, state)
        return left if present(left) else eval_dp_formula("||".join(parts[1:]), ctx, state)

    parts = split_top_level(text, "&&")
    if len(parts) > 1:
        for part in parts:
            if not formula_condition(eval_dp_formula(part, ctx, state)):
                return False
        return True

    parts = split_top_level(text, " or ")
    if len(parts) > 1:
        left = eval_dp_formula(parts[0], ctx, state)
        if isinstance(left, bool):
            return True if left else eval_dp_formula(" or ".join(parts[1:]), ctx, state)
        return left if present(left) else eval_dp_formula(" or ".join(parts[1:]), ctx, state)

    parts = split_top_level(text, "===")
    if len(parts) == 2:
        return compare_formula_value(eval_dp_formula(parts[0], ctx, state)) == compare_formula_value(eval_dp_formula(parts[1], ctx, state))

    parts = split_top_level(text, "==")
    if len(parts) == 2:
        return compare_formula_value(eval_dp_formula(parts[0], ctx, state)) == compare_formula_value(eval_dp_formula(parts[1], ctx, state))

    parts = split_top_level(text, "!=")
    if len(parts) == 2:
        return compare_formula_value(eval_dp_formula(parts[0], ctx, state)) != compare_formula_value(eval_dp_formula(parts[1], ctx, state))

    parts = split_top_level(text, ">=")
    if len(parts) == 2:
        return compare_condition_values(eval_dp_formula(parts[0], ctx, state), eval_dp_formula(parts[1], ctx, state)) >= 0

    parts = split_top_level(text, "<=")
    if len(parts) == 2:
        return compare_condition_values(eval_dp_formula(parts[0], ctx, state), eval_dp_formula(parts[1], ctx, state)) <= 0

    parts = split_top_level(text, ">")
    if len(parts) == 2:
        return compare_condition_values(eval_dp_formula(parts[0], ctx, state), eval_dp_formula(parts[1], ctx, state)) > 0

    parts = split_top_level(text, "<")
    if len(parts) == 2:
        return compare_condition_values(eval_dp_formula(parts[0], ctx, state), eval_dp_formula(parts[1], ctx, state)) < 0

    parts = split_top_level(text, "/")
    if len(parts) > 1:
        value = decimal_formula_value(eval_dp_formula(parts[0], ctx, state))
        for part in parts[1:]:
            divisor = decimal_formula_value(eval_dp_formula(part, ctx, state))
            if divisor == 0:
                raise RawRecipeExecutionError(f"division by zero in formula: ={text}")
            value = value / divisor
        return decimal_formula_result(value)

    parts = split_top_level(text, "-")
    if len(parts) > 1 and parts[0]:
        value = decimal_formula_value(eval_dp_formula(parts[0], ctx, state))
        for part in parts[1:]:
            value -= decimal_formula_value(eval_dp_formula(part, ctx, state))
        return decimal_formula_result(value)

    parts = split_top_level(text, "+")
    if len(parts) > 1:
        # date/datetime + duration, e.g. _dp('...').to_date + 3.months  (or + N.days/weeks/years)
        if len(parts) == 2:
            dur = re.fullmatch(r"\s*(\d+)\.(day|days|week|weeks|month|months|year|years)\s*", parts[1])
            if dur:
                shifted = _shift_date_duration(eval_dp_formula(parts[0], ctx, state), int(dur.group(1)), dur.group(2))
                if shifted is not None:
                    return shifted
        values = [eval_dp_formula(part, ctx, state) for part in parts]
        if len(values) == 2:
            # Ruby Date + Integer counts DAYS — a date-typed pill plus a bare
            # number must never string-join ('2026-06-25' + 14 != '2026-06-2514').
            date_left = _arith_dateonly(values[0])
            if date_left is not None and re.fullmatch(r"\s*-?\d+\s*", str(parts[1])):
                return (date_left + datetime.timedelta(days=int(str(values[1])))).isoformat()
        if all(isinstance(value, (int, Decimal)) and not isinstance(value, bool) for value in values):
            return decimal_formula_result(sum(Decimal(str(value)) for value in values))
        # Lenient string-`+` join (real Ruby raises TypeError on nil +); each
        # segment renders with Ruby to_s parity so a nil/`.presence`-blank
        # segment joins as "" — never the literal 'None'.
        return "".join(ruby_to_s(value) for value in values)

    literal = re.fullmatch(r"\"(.*)\"", text, flags=re.S)
    if literal:
        if "#{" in literal.group(1):
            # Full interpolation first: covers formula fragments inside #{...}
            # (e.g. ternaries on pills). Falls back to the pill-only renderer
            # when the content is not a single literal (bare inner quotes).
            rendered = interpolate_formula_string(literal.group(1), ctx, state)
            if rendered is not None:
                return rendered.replace(r"\"", '"')
        return interpolate_literal_text(literal.group(1), ctx, state)

    single_literal = re.fullmatch(r"'(.*)'", text, flags=re.S)
    if single_literal:
        return single_literal.group(1).replace("\\'", "'")

    number = re.fullmatch(r"-?\d+(?:\.\d+)?", text)
    if number:
        return Decimal(text) if "." in text else int(text)

    if text.startswith("["):
        # Array literal with a method chain, e.g. [_dp(a),_dp(b)].join(" vs ").
        # Left to the mixed-text renderer these silently render as literal text.
        close = matching_bracket_index(text)
        chain = text[close + 1:].strip() if close != -1 else ""
        if close != -1 and chain.startswith((".", "&.")):
            inner = text[1:close].strip()
            elements = (
                [eval_dp_formula(part, ctx, state) for part in split_top_level(inner, ",")]
                if inner
                else []
            )
            return apply_dp_methods(elements, chain, ctx, state)

    # Arithmetic must be attempted BEFORE mixed-text interpolation: texts like
    # `(pill > 0).is_true?` have a non-empty literal remainder, so the mixed
    # path would render them as literal strings (silent wrong answer). An
    # arith evaluation error falls through to the mixed path to preserve the
    # legacy text rendering of genuinely mixed content.
    try:
        arith = _eval_arith_formula(text, ctx, state)
    except RawRecipeExecutionError:
        arith = _ARITH_NOMATCH
    if arith is not _ARITH_NOMATCH:
        return arith

    mixed = interpolate_mixed_dp_formula_text(text, ctx, state)
    if mixed is not None:
        return mixed

    match = re.fullmatch(r"_dp\('([^']+)'\)(.*)", text, flags=re.S)
    if match:
        value = resolve_dp_json(match.group(1), ctx, state)
        return apply_dp_methods(value, match.group(2), ctx, state)

    raise NonRecipeError(f"unsupported formula: ={text}")


# --- General arithmetic engine -------------------------------------------------
# A small recursive-descent evaluator for infix arithmetic (+ - * / %) and
# comparisons over mixed terms (data-calls, datapills, now, numbers, string/
# date literals, parenthesized subexpressions with trailing method chains).
# It is engaged ONLY as a fallback when the regex dispatch above raises, so no
# currently-supported formula changes behavior. Datetime - datetime yields
# elapsed seconds; datetime +/- duration (or +/- a number of seconds) yields a
# datetime.

_ARITH_NOMATCH = object()
_HASH_LITERAL_RE = re.compile(r"\s*\{")
_ARITH_NOW_RE = re.compile(r"now(?:\(\))?(?![A-Za-z0-9_])")
_ARITH_DP_RE = re.compile(r"_dp\('([^']+)'\)")
_ARITH_DATA_RE = re.compile(r"_\('([^']+)'((?:\s*,\s*'[^']*')*)\)")
_ARITH_NUM_RE = re.compile(r"\d+(?:\.\d+)?")
_ARITH_DQ_RE = re.compile(r'"((?:\\.|[^"])*)"', flags=re.S)
_ARITH_SQ_RE = re.compile(r"'((?:\\.|[^'])*)'", flags=re.S)
_ARITH_DURATION_UNITS = {
    "second": "seconds", "seconds": "seconds",
    "minute": "minutes", "minutes": "minutes",
    "hour": "hours", "hours": "hours",
    "day": "days", "days": "days",
    "week": "weeks", "weeks": "weeks",
    "month": "months", "months": "months",
    "year": "years", "years": "years",
}


class _ArithNoMatch(Exception):
    """Signals the arithmetic engine could not confidently parse the text; the
    caller re-raises the original formula error instead."""


class _Duration:
    __slots__ = ("amount", "unit")

    def __init__(self, amount: Any, unit: str) -> None:
        self.amount = amount
        self.unit = _ARITH_DURATION_UNITS[unit]


def _eval_ago_expr(text: str, ctx: RecipeContext) -> Any:
    match = re.fullmatch(r"(\d+)\.(seconds?|minutes?|hours?|days?|weeks?|months?|years?)\.ago", text.strip())
    if not match:
        return _ARITH_NOMATCH
    dt = _seed_now_dt(ctx)
    amount = int(match.group(1))
    unit = _ARITH_DURATION_UNITS[match.group(2)]
    res = _apply_duration(dt, _Duration(amount, unit), -1)
    return res.astimezone(datetime.timezone.utc).isoformat()


def _arith_to_datetime(value: Any) -> datetime.datetime | None:
    if isinstance(value, datetime.datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=datetime.timezone.utc)
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time(), tzinfo=datetime.timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            dt = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            if len(text) == 10:
                try:
                    dt = datetime.datetime.fromisoformat(text + "T00:00:00")
                except ValueError:
                    return None
            else:
                return None
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=datetime.timezone.utc)
    return None


def _arith_is_number(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, Decimal)):
        return True
    if value in (None, MISSING, ""):
        return False
    if isinstance(value, str):
        try:
            Decimal(value.strip())
            return True
        except (InvalidOperation, ValueError):
            return False
    return False


def _arith_num(value: Any) -> Decimal:
    if isinstance(value, bool):
        return Decimal(1) if value else Decimal(0)
    if value in (None, MISSING, ""):
        raise RawRecipeExecutionError("nil/blank operand in arithmetic formula")
    if isinstance(value, (datetime.datetime, datetime.date, _Duration)):
        raise _ArithNoMatch
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise _ArithNoMatch from exc


def _numeric_rounding_method(value: Any, method: str, digits: int) -> int | float:
    """Ruby/Workato numeric round, ceil, and floor semantics.

    The zero/default precision form returns an Integer. A positive precision
    returns a Float, matching Ruby's Numeric methods and the JSON number types
    recorded in replay expectations. Ruby's default ``round`` tie-breaking is
    half away from zero, which Decimal's ROUND_HALF_UP implements exactly.
    """

    if value in (None, MISSING, "") or isinstance(value, bool):
        raise RawRecipeExecutionError(f".{method} on a non-numeric value: {value!r}")
    if abs(digits) > 100:
        raise RawRecipeExecutionError(f".{method} precision is out of range: {digits}")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise RawRecipeExecutionError(
            f".{method} on a non-numeric value: {value!r}"
        ) from exc
    if not number.is_finite():
        raise RawRecipeExecutionError(f".{method} on a non-finite value: {value!r}")

    rounding = {
        "round": ROUND_HALF_UP,
        "ceil": ROUND_CEILING,
        "floor": ROUND_FLOOR,
    }[method]
    quantum = Decimal(1).scaleb(-digits)
    try:
        rounded = number.quantize(quantum, rounding=rounding)
    except InvalidOperation as exc:
        raise RawRecipeExecutionError(
            f".{method} could not round value {value!r} to precision {digits}"
        ) from exc
    return float(rounded) if digits > 0 else int(rounded)


def _beginning_of_period(
    value: Any,
    period: str,
    *,
    week_start: str = "monday",
) -> datetime.date | datetime.datetime:
    """Return the Rails-style beginning of a calendar month or week.

    Date receivers stay dates. Time/datetime receivers retain their timezone
    and become local midnight, so a subsequent ``strftime`` does not drift to
    the previous UTC date. Weeks begin on Monday unless ``:sunday`` is passed.
    """

    date_only = _arith_dateonly(value)
    dt = _arith_to_datetime(value)
    if dt is None:
        raise RawRecipeExecutionError(
            f".beginning_of_{period} on a non-date value: {value!r}"
        )
    if period == "month":
        result = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_weekday = 6 if week_start == "sunday" else 0
        result = (dt - datetime.timedelta(days=(dt.weekday() - start_weekday) % 7)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    return result.date() if date_only is not None else result


def _apply_duration(dt: datetime.datetime, dur: _Duration, sign: int) -> datetime.datetime:
    amount = dur.amount
    unit = dur.unit
    if unit == "months":
        return shift_months(dt, sign * int(amount))
    if unit == "years":
        return shift_months(dt, sign * int(amount) * 12)
    seconds_per = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400, "weeks": 604800}[unit]
    delta = datetime.timedelta(seconds=float(Decimal(str(amount)) * seconds_per))
    return dt + delta if sign >= 0 else dt - delta


def _arith_seconds_between(later: datetime.datetime, earlier: datetime.datetime) -> Any:
    total = (later - earlier).total_seconds()
    if total == int(total):
        return int(total)
    return Decimal(str(total))


def _arith_serialize(value: Any) -> Any:
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, _Duration):
        raise _ArithNoMatch
    return value


def _arith_dateonly(value: Any) -> datetime.date | None:
    if isinstance(value, datetime.datetime):
        return None
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
        return datetime.date.fromisoformat(value.strip())
    return None


def _arith_binop(op: str, left: Any, right: Any) -> Any:
    # Ruby Date arithmetic: Date +/- Integer counts DAYS and Date - Date is a
    # day count — date-only operands must never fall into the Time/seconds
    # branches below.
    date_left = _arith_dateonly(left)
    date_right = _arith_dateonly(right)
    if op == "+":
        if date_left is not None and _arith_is_number(right) and not _arith_is_number(left):
            return date_left + datetime.timedelta(days=int(_arith_num(right)))
        if date_right is not None and _arith_is_number(left) and not _arith_is_number(right):
            return date_right + datetime.timedelta(days=int(_arith_num(left)))
    if op == "-":
        if date_left is not None and date_right is not None:
            return (date_left - date_right).days
        if date_left is not None and _arith_is_number(right) and not _arith_is_number(left):
            return date_left - datetime.timedelta(days=int(_arith_num(right)))
    dl = _arith_to_datetime(left) if not isinstance(left, (int, Decimal, bool, _Duration)) else None
    dr = _arith_to_datetime(right) if not isinstance(right, (int, Decimal, bool, _Duration)) else None
    if op == "+":
        if isinstance(left, list) and isinstance(right, list):
            # Ruby Array + Array concatenation (e.g. pluck(...) + pluck(...)).
            return list(left) + list(right)
        if isinstance(left, _Duration) and dr is not None:
            result = _apply_duration(dr, left, 1)
            if date_right is not None and left.unit in ("days", "weeks", "months", "years"):
                return result.date()  # Ruby Date + n.days stays a Date
            return result
        if isinstance(right, _Duration) and dl is not None:
            result = _apply_duration(dl, right, 1)
            if date_left is not None and right.unit in ("days", "weeks", "months", "years"):
                return result.date()
            return result
        if isinstance(left, _Duration) or isinstance(right, _Duration):
            raise _ArithNoMatch
        if dl is not None and _arith_is_number(right) and not _arith_is_number(left):
            return dl + datetime.timedelta(seconds=float(_arith_num(right)))
        if dr is not None and _arith_is_number(left) and not _arith_is_number(right):
            return dr + datetime.timedelta(seconds=float(_arith_num(left)))
        if dl is not None and dr is not None:
            raise _ArithNoMatch
        # Ruby String + String concatenation: when either side is a
        # non-numeric string, `+` concatenates (nil still raises above via
        # _arith_num when the other side is numeric).
        if (isinstance(left, str) and not _arith_is_number(left)) or (
            isinstance(right, str) and not _arith_is_number(right)
        ):
            if left in (None, MISSING) or right in (None, MISSING):
                raise RawRecipeExecutionError("nil operand in string concatenation")
            return str(left) + str(right)
        return _arith_num(left) + _arith_num(right)
    if op == "-":
        if isinstance(left, list) and isinstance(right, list):
            # Ruby Array difference: keep left order, drop all right matches.
            return [item for item in left if item not in right]
        if isinstance(right, _Duration) and dl is not None:
            result = _apply_duration(dl, right, -1)
            if date_left is not None and right.unit in ("days", "weeks", "months", "years"):
                return result.date()  # Ruby Date - n.days stays a Date
            return result
        if isinstance(left, _Duration) or isinstance(right, _Duration):
            raise _ArithNoMatch
        if dl is not None and dr is not None:
            return _arith_seconds_between(dl, dr)
        if dl is not None and _arith_is_number(right) and not _arith_is_number(left):
            return dl - datetime.timedelta(seconds=float(_arith_num(right)))
        return _arith_num(left) - _arith_num(right)
    if op == "*":
        return _arith_num(left) * _arith_num(right)
    if op == "/":
        divisor = _arith_num(right)
        if divisor == 0:
            raise RawRecipeExecutionError("division by zero in arithmetic formula")

        def _integer_like(value: Any) -> bool:
            if isinstance(value, bool):
                return False
            if isinstance(value, int):
                return True
            # Integer-typed pills reach us as digit strings; Ruby divides
            # them as Integers (floor), never as decimals.
            return isinstance(value, str) and re.fullmatch(r"-?\d+", value.strip()) is not None

        if _integer_like(left) and _integer_like(right):
            return int(_arith_num(left)) // int(divisor)
        return _arith_num(left) / divisor
    if op == "%":
        divisor = _arith_num(right)
        if divisor == 0:
            raise RawRecipeExecutionError("modulo by zero in arithmetic formula")
        return _arith_num(left) % divisor
    raise _ArithNoMatch


def _arith_compare(op: str, left: Any, right: Any) -> bool:
    dl = _arith_to_datetime(left) if not isinstance(left, (int, Decimal, bool)) else None
    dr = _arith_to_datetime(right) if not isinstance(right, (int, Decimal, bool)) else None
    if dl is not None and dr is not None:
        lhs: Any = dl
        rhs: Any = dr
    elif _arith_is_number(left) and _arith_is_number(right):
        lhs, rhs = _arith_num(left), _arith_num(right)
    else:
        lhs, rhs = compare_formula_value(left), compare_formula_value(right)
    if op == "<":
        return lhs < rhs
    if op == ">":
        return lhs > rhs
    if op == "<=":
        return lhs <= rhs
    if op == ">=":
        return lhs >= rhs
    if op == "==":
        return lhs == rhs
    if op == "!=":
        return lhs != rhs
    raise _ArithNoMatch


def _arith_finalize(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, _Duration):
        return _ARITH_NOMATCH
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else value
    return value


def _scan_bracket(text: str, open_idx: int) -> int:
    """Return the index just past the ']' matching the '[' at open_idx, honoring
    quotes so brackets inside string literals do not affect the balance."""
    depth = 0
    quote: str | None = None
    escaped = False
    idx = open_idx
    while idx < len(text):
        char = text[idx]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif quote:
            if char == quote:
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return idx + 1
        idx += 1
    raise _ArithNoMatch


def _extract_brace(text: str, open_idx: int) -> tuple[str, int]:
    depth = 0
    quote: str | None = None
    escaped = False
    idx = open_idx
    while idx < len(text):
        char = text[idx]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif quote:
            if char == quote:
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1:idx], idx + 1
        idx += 1
    raise _ArithNoMatch


def _consume_chain(text: str, idx: int) -> tuple[str, int]:
    """Consume a contiguous Ruby method/index chain starting at idx, e.g.
    .to_i, .in_time_zone("UTC").beginning_of_hour, ["k"], [_('..')]."""
    start = idx
    length = len(text)
    while idx < length:
        char = text[idx]
        if char == "[":
            idx = _scan_bracket(text, idx)
            continue
        if char == "&" and idx + 1 < length and text[idx + 1] == ".":
            after = idx + 2
        elif char == ".":
            after = idx + 1
        else:
            break
        name = re.match(r"[A-Za-z_][A-Za-z0-9_]*[?!]?", text[after:])
        if not name:
            break
        after += name.end()
        if after < length and text[after] == "(":
            _inner, after = _extract_paren(text, after)
        idx = after
    return text[start:idx], idx


def _arith_apply_chain(current: Any, chain: str, ctx: RecipeContext, state: RuntimeState) -> Any:
    rest = chain
    while rest:
        if rest.startswith("&."):
            # Ruby safe navigation, mirroring apply_dp_methods: nil/MISSING
            # receivers skip exactly one method segment (result nil); any
            # other receiver makes `&.` behave as `.` — which also keeps the
            # final apply_dp_methods handoff below byte-identical to the old
            # entry-level `&.` -> `.` rewrite for non-nil values.
            if current is None or current is MISSING:
                current = None
                rest = _consume_safe_nav_segment(rest, chain)
                continue
            rest = "." + rest[2:]
        in_tz = re.match(r'\.in_time_zone\(\s*"((?:\\.|[^"])*)"\s*\)', rest, flags=re.S)
        if not in_tz:
            in_tz = re.match(r"\.in_time_zone\(\s*'((?:\\.|[^'])*)'\s*\)", rest, flags=re.S)
        if not in_tz:
            # Interpolated pill zone: the pill JSON inside #{...} carries
            # double quotes the simple pattern above cannot span. Greedy up to
            # the last `}` that closes the interpolation before `")`.
            in_tz = re.match(r'\.in_time_zone\(\s*"(#\{.*\})"\s*\)', rest, flags=re.S)
        in_tz_dp = None
        if not in_tz:
            # Bare pill arg: .in_time_zone(_dp('{...}')) — the zone comes from
            # a datapill without quoting.
            in_tz_dp = re.match(r"\.in_time_zone\(\s*_dp\('((?:\\.|[^'])*)'\)\s*\)", rest, flags=re.S)
        if in_tz_dp is not None and ctx is not None and state is not None:
            dt = _arith_to_datetime(current)
            if dt is None:
                raise _ArithNoMatch
            zone_value = resolve_dp_json(in_tz_dp.group(1), ctx, state)
            if zone_value in (None, MISSING, ""):
                raise RawRecipeExecutionError("in_time_zone zone pill resolved empty")
            current = dt.astimezone(resolve_zone_info(str(zone_value)))
            rest = rest[in_tz_dp.end():]
            continue
        if in_tz:
            dt = _arith_to_datetime(current)
            if dt is None:
                raise _ArithNoMatch
            zone = decode_workato_string(in_tz.group(1))
            if "#{" in zone:
                # Zone name computed from a datapill, e.g.
                # .in_time_zone("#{_('data.lookup_table...col8')}").
                zone = interpolate_formula_string(zone, ctx, state) or ""
            if not zone:
                raise RawRecipeExecutionError("in_time_zone zone name resolved empty")
            current = dt.astimezone(resolve_zone_info(zone))
            rest = rest[in_tz.end():]
            continue
        beginning_of_month = re.match(
            r"\.beginning_of_month(?:\(\s*\))?(?![A-Za-z0-9_(])",
            rest,
        )
        if beginning_of_month:
            current = _beginning_of_period(current, "month")
            rest = rest[beginning_of_month.end():]
            continue
        beginning_of_week = re.match(
            r"\.beginning_of_week"
            r"(?:\(\s*:(monday|sunday)\s*\)|\(\s*\))?"
            r"(?![A-Za-z0-9_(])",
            rest,
        )
        if beginning_of_week:
            current = _beginning_of_period(
                current,
                "week",
                week_start=beginning_of_week.group(1) or "monday",
            )
            rest = rest[beginning_of_week.end():]
            continue
        if rest.startswith(".beginning_of_hour"):
            dt = _arith_to_datetime(current)
            if dt is None:
                raise _ArithNoMatch
            current = dt.replace(minute=0, second=0, microsecond=0)
            rest = rest[len(".beginning_of_hour"):]
            continue
        if rest.startswith(".beginning_of_day"):
            dt = _arith_to_datetime(current)
            if dt is None:
                raise _ArithNoMatch
            current = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            rest = rest[len(".beginning_of_day"):]
            continue
        to_time = re.match(r"\.to_time(?:\(\))?", rest)
        if to_time:
            time_only = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", _render_text(current, chain).strip())
            if time_only:
                # Ruby "09:00".to_time = today (pinned seed date) at 09:00.
                dt = _seed_now_dt(ctx).replace(
                    hour=int(time_only.group(1)),
                    minute=int(time_only.group(2)),
                    second=int(time_only.group(3) or 0),
                    microsecond=0,
                )
            else:
                dt = _arith_to_datetime(current)
            if dt is None:
                raise _ArithNoMatch
            current = dt
            rest = rest[to_time.end():]
            continue
        to_date = re.match(r"\.to_date(?:\(\))?", rest)
        if to_date:
            dt = _arith_to_datetime(current)
            if dt is None:
                raise _ArithNoMatch
            # Ruby Date: serializes as YYYY-MM-DD (matches workato_to_date in
            # the dp-chain path; a zoned datetime keeps its LOCAL date).
            current = dt.date()
            rest = rest[to_date.end():]
            continue
        strf = re.match(r'\.strftime\(\s*"((?:\\.|[^"])*)"\s*\)', rest, flags=re.S)
        if not strf:
            strf = re.match(r"\.strftime\(\s*'((?:\\.|[^'])*)'\s*\)", rest, flags=re.S)
        if strf:
            dt = _arith_to_datetime(current)
            if dt is None:
                raise _ArithNoMatch
            current = render_strftime(dt, decode_workato_string(strf.group(1)))
            rest = rest[strf.end():]
            continue
        if re.match(r"\.to_i(?![A-Za-z0-9_])", rest):
            if isinstance(current, datetime.datetime):
                current = int(current.timestamp())
            elif isinstance(current, (int, Decimal)) and not isinstance(current, bool):
                current = int(current)
            else:
                match = re.search(r"-?\d+", _render_text(current, chain))
                current = int(match.group(0)) if match else 0
            rest = rest[len(".to_i"):]
            continue
        if re.match(r"\.to_f(?![A-Za-z0-9_])", rest):
            current = _arith_num(current)
            rest = rest[len(".to_f"):]
            continue
        dur = re.match(r"\.(seconds?|minutes?|hours?|days?|weeks?|months?|years?)(?![A-Za-z0-9_])", rest)
        if dur:
            current = _Duration(_arith_num(current), dur.group(1))
            rest = rest[dur.end():]
            continue
        if isinstance(current, _Duration) and rest.startswith(".ago"):
            current = _apply_duration(_seed_now_dt(ctx), current, -1)
            rest = rest[len(".ago"):]
            continue
        if isinstance(current, _Duration) and rest.startswith(".from_now"):
            current = _apply_duration(_seed_now_dt(ctx), current, 1)
            rest = rest[len(".from_now"):]
            continue
        # Any other method/index: hand the remainder to the general chain
        # evaluator with the current value serialized to a form it understands.
        return apply_dp_methods(_arith_serialize(current), rest, ctx, state)
    return current


def _scan_interpolated_dq(s: str, start: int) -> int:
    """Index just past the closing quote of a double-quoted literal at
    `start`, spanning #{...} interpolations whose pill JSON carries quotes.
    Returns -1 when unterminated."""
    idx = start + 1
    while idx < len(s):
        char = s[idx]
        if char == "\\":
            idx += 2
            continue
        if s.startswith("#{", idx):
            depth = 1
            idx += 2
            quote: str | None = None
            while idx < len(s) and depth:
                inner = s[idx]
                if quote:
                    if inner == "\\":
                        idx += 2
                        continue
                    if inner == quote:
                        quote = None
                elif inner in {"'", '"'}:
                    quote = inner
                elif inner == "{":
                    depth += 1
                elif inner == "}":
                    depth -= 1
                idx += 1
            continue
        if char == '"':
            return idx + 1
        idx += 1
    return -1


def _bool_operand_falsy(value: Any) -> bool:
    """Falsiness for Ruby `or`/`and` operands: nil (None/MISSING) and false
    only — Ruby treats "" as truthy. (The former ''-falsy affordance served
    the old `.presence`-blank -> "" encoding; `.presence` now yields nil,
    restoring Ruby parity.)"""
    return value is None or value is False or value is MISSING


class _ArithParser:
    def __init__(self, text: str, ctx: RecipeContext, state: RuntimeState) -> None:
        self.s = text
        self.i = 0
        self.ctx = ctx
        self.state = state

    def skip_ws(self) -> None:
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def parse_expr(self) -> Any:
        # Lowest precedence: Ruby `or` / `and` keywords. Ruby short-circuits;
        # this parser evaluates the rhs eagerly (formula reads are
        # side-effect-free), so an rhs evaluation error surfaces fail-fast
        # even when Ruby would have skipped it.
        value = self.parse_ternary()
        while True:
            self.skip_ws()
            if self._match_word("or"):
                right = self.parse_ternary()
                if _bool_operand_falsy(value):
                    value = right
            elif self._match_word("and"):
                right = self.parse_ternary()
                if not _bool_operand_falsy(value):
                    value = right
            else:
                return value

    def parse_ternary(self) -> Any:
        # Ruby ?: — binds tighter than or/and, looser than comparison. Arms are
        # evaluated LAZILY (span-scanned, only the chosen arm runs), matching
        # Ruby: `x.present? ? x.split(".").last : "none"` must not error on
        # the unchosen arm when x is nil.
        value = self.parse_cmp()
        self.skip_ws()
        if self.i >= len(self.s) or self.s[self.i] != "?":
            return value
        self.i += 1
        colon_idx = self._ternary_colon(self.i)
        end_idx = self._ternary_arm_end(colon_idx + 1)
        true_span = self.s[self.i:colon_idx].strip()
        false_span = self.s[colon_idx + 1:end_idx].strip()
        chosen = false_span if _bool_operand_falsy(value) else true_span
        if not chosen:
            raise _ArithNoMatch
        result = _eval_arith_subexpr(strip_wrapping_parens(chosen), self.ctx, self.state)
        self.i = end_idx
        return result

    def _ternary_colon(self, start: int) -> int:
        depth = 0
        ternaries = 0
        quote: str | None = None
        idx = start
        while idx < len(self.s):
            char = self.s[idx]
            if quote:
                if char == "\\":
                    idx += 2
                    continue
                if char == quote:
                    quote = None
            elif char in {"'", '"'}:
                quote = char
            elif char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
            elif depth == 0 and char == "?":
                ternaries += 1
            elif depth == 0 and char == ":":
                if ternaries == 0:
                    return idx
                ternaries -= 1
            idx += 1
        raise _ArithNoMatch

    def _ternary_arm_end(self, start: int) -> int:
        depth = 0
        quote: str | None = None
        idx = start
        while idx < len(self.s):
            char = self.s[idx]
            if quote:
                if char == "\\":
                    idx += 2
                    continue
                if char == quote:
                    quote = None
            elif char in {"'", '"'}:
                quote = char
            elif char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
            elif depth == 0 and char in "oa":
                match = re.match(r"(?:or|and)\b", self.s[idx:])
                if match and idx > start and self.s[idx - 1].isspace():
                    return idx
            idx += 1
        return len(self.s)

    def _match_word(self, word: str) -> bool:
        end = self.i + len(word)
        if self.s[self.i:end] != word:
            return False
        if end < len(self.s) and (self.s[end].isalnum() or self.s[end] == "_"):
            return False
        if self.i > 0 and (self.s[self.i - 1].isalnum() or self.s[self.i - 1] == "_"):
            return False
        self.i = end
        return True

    def parse_cmp(self) -> Any:
        left = self.parse_add()
        self.skip_ws()
        for op in ("<=", ">=", "==", "!=", "<", ">"):
            if self.s.startswith(op, self.i):
                self.i += len(op)
                right = self.parse_add()
                return _arith_compare(op, left, right)
        return left

    def parse_add(self) -> Any:
        value = self.parse_mul()
        while True:
            self.skip_ws()
            if self.i < len(self.s) and self.s[self.i] in "+-":
                op = self.s[self.i]
                self.i += 1
                value = _arith_binop(op, value, self.parse_mul())
            else:
                return value

    def parse_mul(self) -> Any:
        value = self.parse_unary()
        while True:
            self.skip_ws()
            if self.i < len(self.s) and self.s[self.i] in "*/%":
                op = self.s[self.i]
                self.i += 1
                value = _arith_binop(op, value, self.parse_unary())
            else:
                return value

    def parse_unary(self) -> Any:
        self.skip_ws()
        if self.i < len(self.s) and self.s[self.i] == "-":
            self.i += 1
            return _arith_binop("-", Decimal(0), self.parse_unary())
        if self.i < len(self.s) and self.s[self.i] == "+":
            self.i += 1
            return self.parse_unary()
        return self.parse_primary()

    def parse_primary(self) -> Any:
        self.skip_ws()
        s = self.s
        if self.i >= len(s):
            raise _ArithNoMatch
        if s[self.i] == "(":
            inner, end = _extract_paren(s, self.i)
            self.i = end
            value = _eval_arith_subexpr(inner, self.ctx, self.state)
            return self._chain(value)
        for word, literal in (("true", True), ("false", False), ("nil", None), ("null", None)):
            if s.startswith(word, self.i):
                end = self.i + len(word)
                if end >= len(s) or not (s[end].isalnum() or s[end] == "_"):
                    self.i = end
                    return self._chain(literal)
        if s.startswith("today", self.i):
            end = self.i + len("today")
            if end >= len(s) or not (s[end].isalnum() or s[end] == "_"):
                if s.startswith("()", end):
                    end += 2
                self.i = end
                return self._chain(_seed_now_dt(self.ctx).date())
        match = _ARITH_NOW_RE.match(s, self.i)
        if match:
            self.i = match.end()
            return self._chain(_seed_now_dt(self.ctx))
        match = _ARITH_DP_RE.match(s, self.i)
        if match:
            self.i = match.end()
            return self._chain(resolve_dp_json(match.group(1), self.ctx, self.state))
        match = _ARITH_DATA_RE.match(s, self.i)
        if match:
            self.i = match.end()
            metas = match.group(2)
            if metas:
                meta = re.match(r"\s*,\s*'([^']*)'", metas).group(1)
                value = resolve_data_call(match.group(1), meta, self.state)
            else:
                value = data_path(match.group(1), self.state)
            return self._chain(value)
        match = _ARITH_NUM_RE.match(s, self.i)
        if match:
            self.i = match.end()
            raw = match.group(0)
            return self._chain(Decimal(raw) if "." in raw else int(raw))
        if s[self.i] == '"':
            end = _scan_interpolated_dq(s, self.i)
            if end != -1:
                body = s[self.i + 1:end - 1]
                self.i = end
                if "#{" in body:
                    rendered = interpolate_formula_string(body, self.ctx, self.state)
                    if rendered is None:
                        raise _ArithNoMatch
                    return self._chain(rendered)
                return self._chain(decode_workato_string(body))
        match = _ARITH_DQ_RE.match(s, self.i)
        if match:
            self.i = match.end()
            return self._chain(decode_workato_string(match.group(1)))
        match = _ARITH_SQ_RE.match(s, self.i)
        if match:
            self.i = match.end()
            return self._chain(match.group(1).replace("\\'", "'"))
        raise _ArithNoMatch

    def _chain(self, value: Any) -> Any:
        chain, self.i = _consume_chain(self.s, self.i)
        if chain:
            return _arith_apply_chain(value, chain, self.ctx, self.state)
        return value


def _eval_arith_subexpr(text: str, ctx: RecipeContext, state: RuntimeState) -> Any:
    parser = _ArithParser(text.strip(), ctx, state)
    parser.skip_ws()
    value = parser.parse_expr()
    parser.skip_ws()
    if parser.i != len(parser.s):
        raise _ArithNoMatch
    return value


def _eval_arith_formula(text: str, ctx: RecipeContext, state: RuntimeState) -> Any:
    text = text.strip()
    if not text:
        return _ARITH_NOMATCH
    try:
        value = _eval_arith_subexpr(text, ctx, state)
    except _ArithNoMatch:
        return _ARITH_NOMATCH
    return _arith_finalize(value)


def _parse_hash_literal(text: str, ctx: RecipeContext, state: RuntimeState) -> tuple[dict[str, Any], str]:
    """Parse a Ruby hash literal { key => value, ... } (int or string keys).
    Returns (hash, remainder) where remainder is any trailing chain/index."""
    open_idx = text.index("{")
    inner, end = _extract_brace(text, open_idx)
    remainder = text[end:].strip()
    # Multi-line hash literals may carry inline Ruby comments per line
    # (e.g. `"membership_id" => _dp('...'), # Page 1`).
    if "#" in inner:
        inner = "\n".join(strip_formula_comment(line) for line in inner.splitlines())
    result: dict[str, Any] = {}
    for pair in split_top_level(inner, ","):
        pair = pair.strip()
        if not pair:
            continue
        arrow = find_top_level_token(pair, "=>")
        if arrow == -1:
            raise NonRecipeError(f"unsupported hash literal entry: {pair}")
        key_raw = pair[:arrow].strip()
        value_raw = pair[arrow + 2:].strip()
        key = _hash_key(key_raw)
        result[key] = eval_dp_formula(value_raw, ctx, state)
    return result, remainder


def _hash_key(key_raw: str) -> str:
    number = re.fullmatch(r"-?\d+", key_raw)
    if number:
        return key_raw
    return _strip_quotes(key_raw)


def strip_formula_comment(text: str) -> str:
    """Remove Ruby `# comment` tails from each line, outside quotes and
    slash-regex literals; `#{...}` interpolations are never comments. Lines
    after a comment are preserved (multi-line hash literals carry per-line
    comments)."""
    out: list[str] = []
    quote: str | None = None
    escaped = False
    slash_regex = False
    idx = 0
    while idx < len(text):
        char = text[idx]
        if escaped:
            out.append(char)
            escaped = False
            idx += 1
            continue
        if char == "\\":
            out.append(char)
            escaped = True
            idx += 1
            continue
        if quote:
            if char == quote:
                quote = None
            out.append(char)
            idx += 1
            continue
        # Track slash-delimited regex literals (e.g. gsub(/["']/, ...)) so the
        # quotes inside them do not toggle the quote state and hide a trailing
        # "# comment" line. Mirrors find_top_level_token.
        if slash_regex:
            if char == "/":
                slash_regex = False
            out.append(char)
            idx += 1
            continue
        if char == "/" and idx > 0 and text[idx - 1] == "(":
            slash_regex = True
            out.append(char)
            idx += 1
            continue
        if char in {"'", '"'}:
            quote = char
            out.append(char)
            idx += 1
            continue
        if char == "#" and text[idx + 1 : idx + 2] != "{":
            newline = text.find("\n", idx)
            if newline == -1:
                break
            idx = newline
            continue
        out.append(char)
        idx += 1
    return "".join(out).strip()


def decimal_formula_value(value: Any) -> Decimal:
    if value is MISSING or value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise RawRecipeExecutionError(f"formula value is not numeric: {value}") from exc


def decimal_formula_result(value: Decimal) -> str:
    if value == value.to_integral_value():
        return str(value.quantize(Decimal("1")))
    return format(value.normalize(), "f")


def _consume_safe_nav_segment(rest: str, chain: str) -> str:
    """`nil&.method(...)` — consume exactly ONE method segment (name plus its
    optional argument list) off the front of ``rest`` and return the remaining
    chain; the receiver stays nil. Ruby only skips the single call after the
    `&.`, so a following plain `.method` still runs against nil."""
    name = re.match(r"&\.[A-Za-z_][A-Za-z0-9_]*[?!]?", rest)
    if not name:
        raise NonRecipeError(f"unsupported safe-navigation segment in chain: {chain}")
    after = name.end()
    if after < len(rest) and rest[after] == "(":
        _inner, after = _extract_paren(rest, after)
    return rest[after:]


def _render_text(current: Any, chain: str) -> str:
    """Receiver coercion for the string-taking chain methods (.downcase,
    .gsub, .split, .to_i, ...): nil and false render as "" (established
    engine matrix for `.` string methods on falsy receivers), but an
    unresolved datapill leaf (MISSING) must never reach a string surface —
    ``str(MISSING)`` is a Python object repr, which would silently corrupt
    the rendered output. Fail fast instead (benchmark rules: loud failure
    over silent fallback)."""
    if current is MISSING:
        raise NonRecipeError(
            f"unresolved datapill leaf (MISSING) reached a string render surface in chain: {chain}"
        )
    return str(current or "")


def apply_dp_methods(value: Any, methods: str, ctx: RecipeContext | None = None, state: RuntimeState | None = None) -> Any:
    rest = methods.strip()
    current = value
    while rest:
        # Recipes may carry stray whitespace between chain links,
        # e.g. `.split("_") [0]`.
        stripped = rest.lstrip()
        if not stripped:
            break
        rest = stripped
        if rest.startswith("&."):
            # Ruby safe navigation: `nil&.method(...)` short-circuits to nil
            # WITHOUT evaluating the call; on any other receiver `&.` behaves
            # exactly like `.` (false does NOT short-circuit). An unresolved
            # pill leaf (MISSING) is nil to the recipe, so it short-circuits
            # too. (`&.` used to be rewritten to `.` at entry, which silently
            # dropped the nil guard: nil&.quote rendered the SQL literal
            # 'None' and nil&.strftime raised parsing "None".)
            if current is None or current is MISSING:
                current = None
                rest = _consume_safe_nav_segment(rest, methods)
                continue
            rest = "." + rest[2:]
        two_arg_slice = re.match(r"\[(-?\d+)\s*,\s*(\d+)\]", rest)
        if two_arg_slice:
            # Ruby [start, length] element-reference on strings and lists;
            # negative start counts from the end.
            if current in (MISSING, None):
                raise RawRecipeExecutionError("cannot slice a missing datapill value")
            seq = current if isinstance(current, str) else as_list(current)
            start = int(two_arg_slice.group(1))
            base = start if start >= 0 else len(seq) + start
            length = int(two_arg_slice.group(2))
            # Ruby: out-of-range start -> nil; start == size -> ""/[].
            current = seq[base:base + length] if 0 <= base <= len(seq) else None
            rest = rest[two_arg_slice.end():]
            continue
        range_slice = re.match(r"\[(-?\d+)(\.\.\.?)(-?\d+)\]", rest)
        if range_slice:
            # Ruby range slice: `..` inclusive, `...` exclusive; works on
            # strings and lists. Negative bounds count from the end
            # (`[1..-1]` = from index 1 through the last element).
            start = int(range_slice.group(1))
            end: int | None = int(range_slice.group(3))
            if range_slice.group(2) == "..":
                end = end + 1 if end != -1 else None
            if isinstance(current, str):
                current = current[start:end]
            elif current is not MISSING:
                current = as_list(current)[start:end]
            rest = rest[range_slice.end():]
            continue
        slice_call = re.match(r"\.slice\(\s*(-?\d+)\s*(?:,\s*(\d+)\s*)?\)", rest)
        if slice_call:
            # Ruby slice: str.slice(start, length) -> substring, str.slice(i) ->
            # single element; nil when start is past the end.
            if current in (MISSING, None):
                raise RawRecipeExecutionError("cannot call .slice on a missing datapill value")
            seq = current if isinstance(current, str) else as_list(current)
            start = int(slice_call.group(1))
            base = start if start >= 0 else len(seq) + start
            if slice_call.group(2) is None:
                current = seq[base] if 0 <= base < len(seq) else None
            elif 0 <= base <= len(seq):
                current = seq[base:base + int(slice_call.group(2))]
            else:
                current = None
            rest = rest[slice_call.end():]
            continue
        bare_reverse = re.match(r"\.reverse(?![A-Za-z0-9_(])", rest)
        if bare_reverse:
            if isinstance(current, str):
                current = current[::-1]
            elif current in (MISSING, None):
                raise RawRecipeExecutionError("cannot call .reverse on a missing datapill value")
            else:
                current = list(reversed(as_list(current)))
            rest = rest[bare_reverse.end():]
            continue
        index = re.match(r"\[(\d+)\]", rest)
        if index:
            seq = as_list(current)
            idx = int(index.group(1))
            current = seq[idx] if 0 <= idx < len(seq) else MISSING
            rest = rest[index.end():]
            continue
        # Dynamic index whose value comes from a data-call, e.g.
        # split(",")[_('data.foreach.<line>.index', 'foreach_meta')].
        dynamic_index = re.match(r"\[_\('([^']+)'(?:\s*,\s*'([^']*)')?\)\]", rest)
        if dynamic_index and state is not None:
            index_value = resolve_data_call(dynamic_index.group(1), dynamic_index.group(2) or "", state)
            if isinstance(current, dict) and not any(k in current for k in ("entries", "records", "rows")):
                # Hash-by-key indexing on a plain hash, e.g.
                # _('..message')[_('..key')]. List-wrapper dicts (entries/records/
                # rows) keep the original positional-index behavior below.
                if index_value in (None, MISSING):
                    current = MISSING
                else:
                    key = str(index_value)
                    current = current[key] if key in current else MISSING
            else:
                seq = as_list(current)
                if index_value in (None, MISSING, ""):
                    current = MISSING
                else:
                    idx = int(Decimal(str(index_value)))
                    current = seq[idx] if 0 <= idx < len(seq) else MISSING
            rest = rest[dynamic_index.end():]
            continue
        symbol = re.match(r"\[:([A-Za-z_][A-Za-z0-9_]*)\]", rest)
        if symbol:
            key = symbol.group(1)
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, dict) and key == "entry":
                current = current
            else:
                current = MISSING
            rest = rest[symbol.end():]
            continue
        # String-key bracket access on a hash, e.g. _dp('..')['comments'] or
        # obj["field"]. Dict lookup; MISSING when the key is absent.
        string_index = re.match(r'\[\s*"((?:\\.|[^"])*)"\s*\]', rest, flags=re.S)
        if not string_index:
            string_index = re.match(r"\[\s*'((?:\\.|[^'])*)'\s*\]", rest, flags=re.S)
        if string_index:
            raw_key = string_index.group(1)
            key = decode_workato_string(raw_key) if rest[string_index.start(1) - 1] == '"' else raw_key.replace("\\'", "'")
            if "#{" in key:
                # Interpolated key, e.g. hash["#{_dp('...')}"]; a key that
                # cannot be resolved must fail, not silently miss.
                if ctx is None or state is None:
                    raise NonRecipeError(f"unsupported datapill method chain outside runtime: {methods}")
                resolved_key = interpolate_formula_string(key, ctx, state)
                if resolved_key is None:
                    raise RawRecipeExecutionError(f"hash index interpolation failed: {key!r}")
                key = resolved_key
            if isinstance(current, dict):
                current = current[key] if key in current else MISSING
            else:
                current = MISSING
            rest = rest[string_index.end():]
            continue
        # Computed index, e.g. host.split(".")[host.split(".").length-2].
        # General fallback after the literal/data-call/symbol/string forms:
        # evaluate the bracket body as an arithmetic subexpression.
        if rest.startswith("[") and ctx is not None and state is not None:
            close_idx = _scan_bracket(rest, 0)
            inner_expr = rest[1:close_idx - 1].strip()
            if (
                len(inner_expr) >= 2
                and inner_expr[0] == '"'
                and inner_expr[-1] == '"'
                and "#{" in inner_expr
            ):
                # Interpolated key whose pill JSON carries double quotes, e.g.
                # hash["#{_dp('{"pill_type":...}')}"] — the string_index regex
                # above cannot span those, so interpolate here.
                resolved = interpolate_formula_string(inner_expr[1:-1], ctx, state)
                if resolved is None:
                    raise RawRecipeExecutionError(f"hash index interpolation failed: {inner_expr!r}")
                index_value: Any = resolved
            else:
                try:
                    index_value = _eval_arith_subexpr(inner_expr, ctx, state)
                except _ArithNoMatch:
                    raise NonRecipeError(f"unsupported datapill index expression: {inner_expr!r} in {methods}")
            if isinstance(current, dict):
                key = "" if index_value in (None, MISSING) else str(index_value)
                current = current[key] if key in current else MISSING
            elif index_value in (None, MISSING, ""):
                current = MISSING
            else:
                seq = as_list(current)
                idx = int(Decimal(str(index_value)))
                current = seq[idx] if -len(seq) <= idx < len(seq) else MISSING
            rest = rest[close_idx:]
            continue
        if rest.startswith(".presence"):
            # Rails parity: blank -> nil (see the eval_formula `.presence` site).
            current = current if present(current) else None
            rest = rest[len(".presence"):]
            continue
        if rest.startswith(".present?"):
            current = present(current)
            rest = rest[len(".present?"):]
            continue
        if rest.startswith(".blank?"):
            current = not present(current)
            rest = rest[len(".blank?"):]
            continue
        if rest.startswith(".quote"):
            current = quote_sql_literal(current)
            rest = rest[len(".quote"):]
            continue
        if rest.startswith(".is_not_true?"):
            current = not truthy(current)
            rest = rest[len(".is_not_true?"):]
            continue
        if rest.startswith(".is_true?"):
            current = truthy(current)
            rest = rest[len(".is_true?"):]
            continue
        size_or_length = re.match(r"\.(size|length)(?![A-Za-z0-9_(])", rest)
        if size_or_length:
            # Ruby: String/Array/Hash #length and #size are aliases; nothing
            # else a recipe reaches has either (Integer#length raises
            # NoMethodError, Integer#size is the machine byte width — never
            # what a formula wants). One branch, one semantics: len() for
            # sized values, loud failure for everything else. (Previously two
            # branches that disagreed: a startswith(".length") one here and a
            # shadowed `.size|.length` twin further down whose int digit-count
            # fallback nothing in the corpus uses — no recipe calls .size at
            # all and none calls .length on a number.)
            method = size_or_length.group(1)
            if current is MISSING or current is None:
                raise RawRecipeExecutionError(f"cannot call .{method} on a missing datapill value")
            if not isinstance(current, (list, tuple, dict, str)):
                raise RawRecipeExecutionError(f"cannot call .{method} on value type: {type(current).__name__}")
            current = len(current)
            rest = rest[size_or_length.end():]
            continue
        if rest.startswith(".first()"):
            seq = as_list(current)
            current = seq[0] if seq else MISSING
            rest = rest[len(".first()"):]
            continue
        if rest.startswith(".first"):
            seq = as_list(current)
            current = seq[0] if seq else MISSING
            rest = rest[len(".first"):]
            continue
        if rest.startswith(".last()"):
            seq = as_list(current)
            current = seq[-1] if seq else MISSING
            rest = rest[len(".last()"):]
            continue
        bare_last = re.match(r"\.last(?![A-Za-z0-9_(])", rest)
        if bare_last:
            seq = as_list(current)
            current = seq[-1] if seq else MISSING
            rest = rest[bare_last.end():]
            continue
        bare_to_s = re.match(r"\.to_s(?![A-Za-z0-9_(])", rest)
        if bare_to_s:
            current = ruby_to_s(current)
            rest = rest[bare_to_s.end():]
            continue
        bare_to_currency = re.match(r"\.to_currency(?![A-Za-z0-9_(])", rest)
        if bare_to_currency:
            try:
                amount = Decimal(str(current))
            except (InvalidOperation, ValueError) as exc:
                raise RawRecipeExecutionError(f".to_currency on non-numeric value: {current!r}") from exc
            sign = "-" if amount < 0 else ""
            current = f"{sign}${abs(amount):,.2f}"
            rest = rest[bare_to_currency.end():]
            continue
        numeric_rounding = re.match(
            r"\.(round|ceil|floor)"
            r"(?:\(\s*(-?\d+)\s*\)|\(\s*\))?"
            r"(?![A-Za-z0-9_(])",
            rest,
        )
        if numeric_rounding:
            digits = int(numeric_rounding.group(2) or 0)
            current = _numeric_rounding_method(
                current,
                numeric_rounding.group(1),
                digits,
            )
            rest = rest[numeric_rounding.end():]
            continue
        format_map = re.match(
            r"\.format_map\((?:'((?:\\.|[^'])*)'|\"((?:\\.|[^\"])*)\")\)", rest, flags=re.S
        )
        if format_map:
            # Ruby format_map: %{key} substitutes per-row hash fields; %s
            # substitutes the row itself (scalar rows, e.g. quoted SQL IN lists).
            raw_template = format_map.group(1) if format_map.group(1) is not None else format_map.group(2)
            template = raw_template.replace("\\'", "'").replace('\\"', '"')
            def _format_row(row: Any, _template: str = template) -> str:
                out = re.sub(
                    r"%\{([^}]+)\}",
                    lambda m: "" if (v := field_value(row, m.group(1))) in (None, MISSING) else str(v),
                    _template,
                )
                if "%s" in out:
                    if isinstance(row, (dict, list)):
                        raise NonRecipeError(f"format_map positional %s applied to a non-scalar row: {row!r}")
                    out = out.replace("%s", "" if row in (None, MISSING) else str(row))
                return out
            current = [_format_row(row) for row in as_list(current)]
            rest = rest[format_map.end():]
            continue
        # Multi-argument pluck of nested paths, e.g.
        # .pluck(['entry','col1'],['entry','col2']) -> one array per row.
        multi_pluck = re.match(r"\.pluck\((\[[^\]]*\](?:\s*,\s*\[[^\]]*\])+)\)", rest)
        if multi_pluck:
            paths: list[list[str]] = []
            for group in re.findall(r"\[([^\]]*)\]", multi_pluck.group(1)):
                keys = [single or double for single, double in re.findall(r"'([^']+)'|\"([^\"]+)\"", group)]
                if not keys:
                    raise NonRecipeError(f"unsupported datapill method chain: {methods}")
                paths.append(keys)
            current = [[lookup_path(row, keys) for keys in paths] for row in as_list(current)]
            rest = rest[multi_pluck.end():]
            continue
        nested_pluck = re.match(r"\.pluck\(\[([^\]]+)\]\)", rest)
        if nested_pluck:
            path = re.findall(r"'([^']+)'|\"([^\"]+)\"", nested_pluck.group(1))
            keys = [single or double for single, double in path]
            if not keys:
                raise NonRecipeError(f"unsupported datapill method chain: {methods}")
            current = [lookup_path(row, keys) for row in as_list(current)]
            rest = rest[nested_pluck.end():]
            continue
        pluck = re.match(r"\.pluck\('([^']+)'\)", rest)
        if pluck:
            current = [field_value(row, pluck.group(1)) for row in as_list(current)]
            rest = rest[pluck.end():]
            continue
        double_pluck = re.match(r'\.pluck\("((?:\\.|[^"])*)"\)', rest, flags=re.S)
        if double_pluck:
            current = [field_value(row, decode_workato_string(double_pluck.group(1))) for row in as_list(current)]
            rest = rest[double_pluck.end():]
            continue
        symbol_pluck = re.match(r"\.pluck\(:([A-Za-z_][A-Za-z0-9_]*)\)", rest)
        if symbol_pluck:
            current = [field_value(row, symbol_pluck.group(1)) for row in as_list(current)]
            rest = rest[symbol_pluck.end():]
            continue
        if rest.startswith(".compact"):
            current = [value for value in as_list(current) if present(value)]
            rest = rest[len(".compact"):]
            continue
        if rest.startswith(".uniq"):
            seen: set[str] = set()
            unique: list[Any] = []
            for item in as_list(current):
                key = str(item)
                if key in seen:
                    continue
                seen.add(key)
                unique.append(item)
            current = unique
            rest = rest[len(".uniq"):]
            continue
        join = re.match(r'\.join\("((?:\\.|[^"])*)"\)', rest, flags=re.S)
        if join:
            delimiter = decode_workato_string(join.group(1))
            current = delimiter.join("" if value is MISSING else str(value) for value in as_list(current))
            rest = rest[join.end():]
            continue
        single_join = re.match(r"\.join\('((?:\\.|[^'])*)'\)", rest, flags=re.S)
        if single_join:
            delimiter = decode_workato_string(single_join.group(1))
            current = delimiter.join("" if value is MISSING else str(value) for value in as_list(current))
            rest = rest[single_join.end():]
            continue
        if rest.startswith(".downcase"):
            current = _render_text(current, methods).lower()
            rest = rest[len(".downcase"):]
            continue
        if rest.startswith(".upcase"):
            current = _render_text(current, methods).upper()
            rest = rest[len(".upcase"):]
            continue
        if rest.startswith(".capitalize"):
            text = _render_text(current, methods)
            current = text[:1].upper() + text[1:].lower()
            rest = rest[len(".capitalize"):]
            continue
        text_codec = re.match(
            r"\.(encode_base64|decode_base64|encode_url|decode_url)"
            r"(?:\(\))?(?![A-Za-z0-9_(])",
            rest,
        )
        if text_codec:
            method = text_codec.group(1)
            if current is MISSING or current is None:
                raise RawRecipeExecutionError(f".{method} on a missing datapill value")
            if not isinstance(current, str):
                raise RawRecipeExecutionError(
                    f".{method} on a non-string value: {current!r}"
                )
            if method == "encode_base64":
                current = base64.b64encode(current.encode("utf-8")).decode("ascii")
            elif method == "decode_base64":
                # API payloads such as GitHub's may wrap base64 across lines;
                # tolerate ASCII whitespace but validate every encoded byte.
                encoded = re.sub(r"\s+", "", current)
                try:
                    decoded = base64.b64decode(encoded, validate=True)
                    current = decoded.decode("utf-8")
                except (binascii.Error, UnicodeDecodeError) as exc:
                    raise RawRecipeExecutionError(
                        ".decode_base64 received invalid base64 UTF-8 text"
                    ) from exc
            elif method == "encode_url":
                current = urllib.parse.quote(current, safe="")
            else:
                if re.search(r"%(?![0-9A-Fa-f]{2})", current):
                    raise RawRecipeExecutionError(
                        ".decode_url received malformed percent encoding"
                    )
                try:
                    current = urllib.parse.unquote_to_bytes(current).decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise RawRecipeExecutionError(
                        ".decode_url received invalid UTF-8 text"
                    ) from exc
            rest = rest[text_codec.end():]
            continue
        if rest.startswith(".titleize"):
            text = _render_text(current, methods).replace("_", " ")
            current = re.sub(r"[A-Za-z0-9]+", lambda match: match.group(0).capitalize(), text)
            rest = rest[len(".titleize"):]
            continue
        if rest.startswith(".lstrip"):
            current = _render_text(current, methods).lstrip()
            rest = rest[len(".lstrip"):]
            continue
        if rest.startswith(".rstrip"):
            current = _render_text(current, methods).rstrip()
            rest = rest[len(".rstrip"):]
            continue
        if rest.startswith(".strip_tags"):
            current = re.sub(r"<[^>]*>", "", _render_text(current, methods))
            rest = rest[len(".strip_tags"):]
            continue
        if rest.startswith(".strip"):
            current = _render_text(current, methods).strip()
            rest = rest[len(".strip"):]
            continue
        if rest.startswith(".to_time"):
            text_value = _render_text(current, methods).strip()
            if not text_value:
                raise RawRecipeExecutionError(".to_time on a blank value")
            time_only = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", text_value)
            if time_only:
                # Ruby "09:00".to_time = today at 09:00 (pinned seed date).
                if ctx is None:
                    raise NonRecipeError(".to_time on a time-only value requires runtime context")
                base = _seed_now_dt(ctx)
                parsed = base.replace(
                    hour=int(time_only.group(1)),
                    minute=int(time_only.group(2)),
                    second=int(time_only.group(3) or 0),
                    microsecond=0,
                )
            else:
                parsed = _arith_to_datetime(text_value)
            if parsed is None:
                raise RawRecipeExecutionError(f".to_time cannot parse {text_value!r}")
            current = parsed.isoformat()
            rest = rest[len(".to_time"):]
            continue
        if rest.startswith(".yweek"):
            parsed = _arith_to_datetime(current)
            if parsed is None:
                raise RawRecipeExecutionError(f".yweek on a non-date value: {current!r}")
            current = parsed.isocalendar()[1]
            rest = rest[len(".yweek"):]
            continue
        if rest.startswith(".to_date"):
            current = workato_to_date(current)
            rest = rest[len(".to_date"):]
            continue
        # Zone captured lazily up to the closing `").strftime(` so interpolated
        # datapill zones (whose pill JSON contains double quotes) are spanned.
        in_tz_strftime = re.match(
            r'\.in_time_zone\("(.*?)"\)\.strftime\("((?:\\.|[^"])*)"\)',
            rest,
            flags=re.S,
        )
        if in_tz_strftime:
            zone = decode_workato_string(in_tz_strftime.group(1))
            if ctx is not None and state is not None and "#{" in zone:
                zone = interpolate_formula_string(zone, ctx, state) or interpolate_literal_text(zone, ctx, state)
            fmt = decode_workato_string(in_tz_strftime.group(2))
            if current is None or current is MISSING:
                # Rails: nil.in_time_zone is NoMethodError (a job error) — the
                # plain-dot path must surface a recipe-visible error, never the
                # ISO parser's raw ValueError on the rendered string "None".
                # (nil under `&.in_time_zone` short-circuits in the safe-nav
                # handler above and never reaches this branch; an unresolved
                # pill leaf (MISSING) is nil to the recipe.)
                raise RawRecipeExecutionError(".in_time_zone on a missing datapill value")
            try:
                dt = datetime.datetime.fromisoformat(str(current).replace("Z", "+00:00"))
            except ValueError as exc:
                raise RawRecipeExecutionError(
                    f".in_time_zone on a non-datetime value: {current!r}"
                ) from exc
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            current = render_strftime(dt.astimezone(resolve_zone_info(zone)), fmt)
            rest = rest[in_tz_strftime.end():]
            continue
        strftime = re.match(r'\.strftime\("((?:\\.|[^"])*)"\)', rest, flags=re.S)
        if strftime:
            current = strftime_workato(current, decode_workato_string(strftime.group(1)))
            rest = rest[strftime.end():]
            continue
        # gsub whose PATTERN embeds pill interpolation, e.g.
        # .gsub("#{_dp('{"pill_type":...}')} v", "") - the pill JSON carries
        # bare double quotes, so the plain string_gsub regex below can never
        # match it. Render the pattern with the standard literal interpolator,
        # then replace (Ruby string-pattern gsub semantics).
        interp_gsub = re.match(
            r'\.gsub\("('
            r'(?:#\{[^{}]*(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}[^{}]*)*\}|\\.|[^"])*'
            r')"\s*,\s*"((?:\\.|[^"])*)"\)',
            rest,
            flags=re.S,
        )
        if (
            interp_gsub
            and "#{" in interp_gsub.group(1)
            and ctx is not None
            and state is not None
        ):
            pattern_text = interpolate_literal_text(interp_gsub.group(1), ctx, state)
            replacement = decode_workato_string(interp_gsub.group(2))
            current = _render_text(current, methods).replace(pattern_text, replacement)
            rest = rest[interp_gsub.end():]
            continue
        string_gsub = re.match(r'\.gsub\("((?:\\.|[^"])*)"\s*,\s*"((?:\\.|[^"])*)"\)', rest, flags=re.S)
        if string_gsub:
            current = _render_text(current, methods).replace(
                decode_workato_string(string_gsub.group(1)),
                decode_workato_string(string_gsub.group(2)),
            )
            rest = rest[string_gsub.end():]
            continue
        # Single-quoted gsub args (mixed quoting like .gsub('"', "'") too):
        # single-quoted Ruby strings only escape \' and \\, no escape decoding.
        single_gsub = re.match(
            r"\.gsub\("
            r"(?:'((?:\\.|[^'])*)'|\"((?:\\.|[^\"])*)\")\s*,\s*"
            r"(?:'((?:\\.|[^'])*)'|\"((?:\\.|[^\"])*)\")\)",
            rest,
            flags=re.S,
        )
        if single_gsub and (single_gsub.group(1) is not None or single_gsub.group(3) is not None):
            pattern = (
                single_gsub.group(1).replace("\\'", "'").replace("\\\\", "\\")
                if single_gsub.group(1) is not None
                else decode_workato_string(single_gsub.group(2))
            )
            replacement = (
                single_gsub.group(3).replace("\\'", "'").replace("\\\\", "\\")
                if single_gsub.group(3) is not None
                else decode_workato_string(single_gsub.group(4))
            )
            current = _render_text(current, methods).replace(pattern, replacement)
            rest = rest[single_gsub.end():]
            continue
        dp_gsub = re.match(r'\.gsub\("((?:\\.|[^"])*)",\s*"#\{_dp\(\'(.*?)\'\)\}"\)', rest, flags=re.S)
        if dp_gsub and ctx is not None and state is not None:
            replacement = resolve_dp_json(dp_gsub.group(2), ctx, state)
            current = _render_text(current, methods).replace(decode_workato_string(dp_gsub.group(1)), "" if replacement is MISSING else str(replacement))
            rest = rest[dp_gsub.end():]
            continue
        regex_gsub = re.match(r'\.gsub\(/((?:\\/|[^/])*)/,\s*"((?:\\.|[^"])*)"\)', rest, flags=re.S)
        if regex_gsub:
            pattern = regex_gsub.group(1).replace("\\/", "/")
            current = re.sub(pattern, decode_workato_string(regex_gsub.group(2)), _render_text(current, methods))
            rest = rest[regex_gsub.end():]
            continue
        # Single-quoted replacement, e.g. .gsub(/re/, '<\4|\2>'). Ruby \N group
        # backreferences are converted to Python \g<N> so digit-adjacent refs are
        # unambiguous; a single-quoted Ruby string only escapes \' and \\.
        regex_gsub_single = re.match(r"\.gsub\(/((?:\\/|[^/])*)/,\s*'((?:\\.|[^'])*)'\)", rest, flags=re.S)
        if regex_gsub_single:
            pattern = regex_gsub_single.group(1).replace("\\/", "/")
            replacement = regex_gsub_single.group(2).replace("\\'", "'").replace("\\\\", "\\")
            replacement = re.sub(r"\\(\d+)", r"\\g<\1>", replacement)
            current = re.sub(pattern, replacement, _render_text(current, methods))
            rest = rest[regex_gsub_single.end():]
            continue
        # Ruby gsub with a hash replacement, e.g. .gsub(/["']/, '"'=>'', '\''=>"''")
        regex_hash_gsub = re.match(r"\.gsub\(/((?:\\/|[^/])*)/\s*,\s*", rest, flags=re.S)
        if regex_hash_gsub:
            tail = rest[regex_hash_gsub.end():]
            pair_re = re.compile(
                r"\s*('(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\")\s*=>\s*('(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\")\s*(,)?",
                flags=re.S,
            )

            def _unquote(token: str) -> str:
                body = token[1:-1]
                return body.replace("\\'", "'") if token[0] == "'" else decode_workato_string(body)

            mapping: dict[str, str] = {}
            pos = 0
            while True:
                pair = pair_re.match(tail, pos)
                if not pair:
                    break
                mapping[_unquote(pair.group(1))] = _unquote(pair.group(2))
                pos = pair.end()
                if not pair.group(3):
                    break
            if mapping and pos < len(tail) and tail[pos] == ")":
                pattern = regex_hash_gsub.group(1).replace("\\/", "/")
                current = re.sub(pattern, lambda m: mapping.get(m.group(0), m.group(0)), _render_text(current, methods))
                rest = tail[pos + 1:]
                continue
        split = re.match(r'\.split\("((?:\\.|[^"])*)"\)', rest, flags=re.S)
        if split:
            current = _render_text(current, methods).split(decode_workato_string(split.group(1)))
            rest = rest[split.end():]
            continue
        split_single = re.match(r"\.split\('((?:\\.|[^'])*)'\)", rest, flags=re.S)
        if split_single:
            current = _render_text(current, methods).split(split_single.group(1).replace("\\'", "'"))
            rest = rest[split_single.end():]
            continue
        smart_join = re.match(r'\.smart_join\("((?:\\.|[^"])*)"\)', rest, flags=re.S)
        if smart_join:
            delimiter = decode_workato_string(smart_join.group(1))
            current = delimiter.join(str(value) for value in as_list(current) if present(value))
            rest = rest[smart_join.end():]
            continue
        if rest.startswith(".to_i"):
            match = re.search(r"-?\d+", _render_text(current, methods))
            current = int(match.group(0)) if match else 0
            rest = rest[len(".to_i"):]
            continue
        if rest.startswith(".to_json"):
            if current is not MISSING:
                current = json.dumps(current, separators=(",", ":"), sort_keys=True)
            rest = rest[len(".to_json"):]
            continue
        regex = re.match(r"\.match\?\(/((?:\\/|[^/])*)/\)", rest, flags=re.S)
        if regex:
            pattern = regex.group(1).replace("\\/", "/")
            current = re.search(pattern, _render_text(current, methods)) is not None
            rest = rest[regex.end():]
            continue
        concat_dp = re.match(r"\.concat\(\s*_dp\('((?:\\.|[^'])*)'\)\s*\)", rest, flags=re.S)
        if concat_dp and ctx is not None and state is not None:
            other = resolve_dp_json(concat_dp.group(1), ctx, state)
            if current in (None, MISSING):
                # Ruby: nil.concat raises NoMethodError (a nil receiver under
                # `&.concat` short-circuits in the safe-navigation handler
                # above and never reaches this branch; the corpus only ever
                # writes `&.concat`).
                raise RawRecipeExecutionError("cannot call .concat on a missing datapill value")
            elif isinstance(current, list):
                if not isinstance(other, list):
                    raise RawRecipeExecutionError(
                        f"Array#concat argument is not an array: {other!r}"
                    )
                current = list(current) + list(other)
            elif isinstance(current, str):
                if other in (None, MISSING):
                    raise RawRecipeExecutionError("String#concat argument is nil")
                current = current + str(other)
            else:
                raise NonRecipeError(f"unsupported .concat receiver: {type(current).__name__}")
            rest = rest[concat_dp.end():]
            continue
        include_dp = re.match(r"\.include\?\(\s*_dp\('((?:\\.|[^'])*)'\)\s*\)", rest, flags=re.S)
        if include_dp and ctx is not None and state is not None:
            needle = resolve_dp_json(include_dp.group(1), ctx, state)
            needle_text = "" if needle in (None, MISSING) else str(needle)
            if isinstance(current, list):
                # Ruby Array#include? — element membership, not substring.
                current = any(str(item) == needle_text for item in current)
            else:
                current = needle_text in _render_text(current, methods)
            rest = rest[include_dp.end():]
            continue
        include = re.match(r'\.include\?\("((?:\\.|[^"])*)"\)', rest, flags=re.S)
        if include:
            needle = decode_workato_string(include.group(1))
            if isinstance(current, list):
                # Ruby Array#include? — element membership, not repr substring.
                current = any(str(item) == needle for item in current)
            else:
                current = needle in _render_text(current, methods)
            rest = rest[include.end():]
            continue
        if rest.startswith(".keys") and not rest.startswith(".keys_"):
            if not isinstance(current, dict):
                raise RawRecipeExecutionError(f".keys on a non-hash value: {current!r}")
            current = list(current.keys())
            rest = rest[len(".keys"):]
            continue
        if rest.startswith(".utc") and not rest.startswith((".utc_", ".utcn")):
            # Ruby Time#utc — convert to UTC (commonly chained into strftime).
            dt = _arith_to_datetime(current)
            if dt is None:
                raise RawRecipeExecutionError(f".utc on a non-datetime value: {current!r}")
            current = dt.astimezone(datetime.timezone.utc)
            rest = rest[len(".utc"):]
            continue
        if rest.startswith(".wday") and not rest.startswith(".wday_"):
            # Ruby Date#wday: 0=Sunday..6=Saturday.
            dt = _arith_to_datetime(current)
            if dt is None:
                raise RawRecipeExecutionError(f".wday on a non-date value: {current!r}")
            current = dt.isoweekday() % 7
            rest = rest[len(".wday"):]
            continue
        ends_with = re.match(r'\.ends_with\?\("((?:\\.|[^"])*)"\)', rest, flags=re.S)
        if ends_with:
            current = _render_text(current, methods).endswith(decode_workato_string(ends_with.group(1)))
            rest = rest[ends_with.end():]
            continue
        starts_with = re.match(r'\.starts_with\?\("((?:\\.|[^"])*)"\)', rest, flags=re.S)
        if starts_with:
            current = _render_text(current, methods).startswith(decode_workato_string(starts_with.group(1)))
            rest = rest[starts_with.end():]
            continue
        starts_with_single = re.match(r"\.starts_with\?\('((?:\\.|[^'])*)'\)", rest, flags=re.S)
        if starts_with_single:
            current = _render_text(current, methods).startswith(starts_with_single.group(1).replace("\\'", "'"))
            rest = rest[starts_with_single.end():]
            continue
        unicode_normalize = re.match(r"\.unicode_normalize(?:\(:(nfc|nfd|nfkc|nfkd)\))?(?![A-Za-z0-9_(])", rest)
        if unicode_normalize:
            # Ruby String#unicode_normalize defaults to :nfc.
            form = (unicode_normalize.group(1) or "nfc").upper()
            current = unicodedata.normalize(form, _render_text(current, methods))
            rest = rest[unicode_normalize.end():]
            continue
        # Numeric modulo, e.g. _('...').Secs % 10 -> int remainder.
        modulo = re.match(r"\s*%\s*(\d+)", rest)
        if modulo:
            divisor = int(modulo.group(1))
            dividend = Decimal(str(current)) if current not in (None, MISSING, "") else Decimal("0")
            result = dividend % divisor
            current = int(result) if result == result.to_integral_value() else result
            rest = rest[modulo.end():]
            continue
        bare_sum = re.match(r"\.sum(?![A-Za-z0-9_(])", rest)
        if bare_sum:
            total = Decimal(0)
            for item in as_list(current):
                if item in (None, MISSING, ""):
                    continue
                try:
                    total += Decimal(str(item))
                except (InvalidOperation, ValueError) as exc:
                    raise RawRecipeExecutionError(f".sum over non-numeric value: {item!r}") from exc
            current = int(total) if total == total.to_integral_value() else total
            rest = rest[bare_sum.end():]
            continue
        bare_min = re.match(r"\.min(?![A-Za-z0-9_])", rest)
        if bare_min:
            current = _numeric_extreme(as_list(current), min)
            rest = rest[bare_min.end():]
            continue
        bare_max = re.match(r"\.max(?![A-Za-z0-9_])", rest)
        if bare_max:
            current = _numeric_extreme(as_list(current), max)
            rest = rest[bare_max.end():]
            continue
        # list-of-hashes filter, e.g. .where(label: ["A","B"]),
        # .where("label !=": "X"), .where(validFor: "2").
        where_head = re.match(r"\.where\s*\(", rest)
        if where_head:
            inner, after_idx = _extract_paren(rest, where_head.end() - 1)
            current = _apply_where(as_list(current), inner, ctx, state)
            rest = rest[after_idx:]
            continue
        if rest.startswith(".to_csv"):
            items = as_list(current)
            if items and all(isinstance(item, list) for item in items):
                current = "".join(_csv_line(item) for item in items)
            else:
                current = _csv_line(items)
            rest = rest[len(".to_csv"):]
            continue
        or_call = re.match(r"\s*or\s+_\('([^']+)'(?:,\s*'([^']+)')?\)", rest)
        if or_call:
            # Ruby `pill or _('...')` fallback inside a datapill chain: nil and
            # false take the right-hand data call; any other value (including
            # an empty string, per Ruby truthiness) keeps the left side.
            if state is None:
                raise NonRecipeError(f"unsupported datapill method chain outside runtime: {methods}")
            if current is None or current is MISSING or current is False:
                current = resolve_data_call(or_call.group(1), or_call.group(2) or "", state)
            rest = rest[or_call.end():]
            continue
        raise NonRecipeError(f"unsupported datapill method chain: {methods}")
    return current


def _numeric_extreme(items: list[Any], chooser: Callable[..., Any]) -> Any:
    values = [item for item in items if item not in (None, MISSING, "")]
    if not values:
        return MISSING
    try:
        return chooser(values, key=lambda item: Decimal(str(item)))
    except (InvalidOperation, ValueError):
        return chooser(values, key=lambda item: str(item))


def _csv_line(cells: list[Any]) -> str:
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerow(
        ["" if cell in (None, MISSING) else str(cell) for cell in cells]
    )
    return buffer.getvalue()


def _split_where_conditions(inner: str) -> list[str]:
    """Split a .where(...) argument list on top-level commas, respecting
    quotes and (), [], {} nesting (array values contain commas)."""
    parts: list[str] = []
    depth = 0
    quote: str | None = None
    escaped = False
    start = 0
    for idx, char in enumerate(inner):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char in "([{":
            depth += 1
            continue
        if char in ")]}":
            depth = max(0, depth - 1)
            continue
        if char == "," and depth == 0:
            parts.append(inner[start:idx])
            start = idx + 1
    parts.append(inner[start:])
    return parts


def _apply_where(rows: list[Any], inner: str, ctx: RecipeContext | None, state: RuntimeState | None) -> list[Any]:
    conditions: list[tuple[str, str, Any]] = []
    for part in _split_where_conditions(inner):
        text = part.strip()
        if not text:
            continue
        colon = find_top_level_token(text, ":")
        if colon == -1:
            raise NonRecipeError(f"unsupported .where filter: {inner}")
        key_raw = _strip_quotes(text[:colon].strip())
        value_expr = text[colon + 1:].strip()
        operator_match = re.fullmatch(r"(.+?)\s*(!=|<>|=)\s*", key_raw)
        if operator_match:
            field = operator_match.group(1).strip()
            op = "!=" if operator_match.group(2) in {"!=", "<>"} else "=="
        else:
            field = key_raw
            op = "=="
        conditions.append((field, op, _eval_where_value(value_expr, ctx, state)))
    if not conditions:
        raise NonRecipeError(f"unsupported .where filter: {inner}")
    return [
        row
        for row in rows
        if all(_where_condition_keeps(row, field, op, value) for field, op, value in conditions)
    ]


def _where_condition_keeps(row: Any, field: str, op: str, value: Any) -> bool:
    actual = field_value(row, field)
    if isinstance(value, re.Pattern):
        matched = actual not in (None, MISSING) and value.search(str(actual)) is not None
        return not matched if op == "!=" else matched
    if value is None:
        # Ruby nil: only nil/absent match (empty string is NOT nil).
        is_nil = actual is None or actual is MISSING
        return not is_nil if op == "!=" else is_nil
    if isinstance(value, list):
        contained = any(str(actual) == str(candidate) for candidate in value)
        return not contained if op == "!=" else contained
    if op == "!=":
        return str(actual if actual is not None else "") != str(value)
    return str(actual if actual is not None else "") == str(value)


def _eval_where_value(expr: str, ctx: RecipeContext | None, state: RuntimeState | None) -> Any:
    expr = expr.strip()
    if expr == "nil":
        return None
    regex_literal = re.fullmatch(r"/((?:\\/|[^/])*)/([im]*)", expr, flags=re.S)
    if regex_literal:
        flags = (re.I if "i" in regex_literal.group(2) else 0) | (re.S if "m" in regex_literal.group(2) else 0)
        return re.compile(regex_literal.group(1).replace("\\/", "/"), flags)
    if ctx is not None and state is not None:
        return eval_dp_formula(expr, ctx, state)
    if expr.startswith("[") and expr.endswith("]"):
        inner = expr[1:-1].strip()
        return [_strip_quotes(part.strip()) for part in split_top_level(inner, ",")] if inner else []
    return _strip_quotes(expr)


def interpolate_mixed_dp_formula_text(text: str, ctx: RecipeContext, state: RuntimeState) -> str | None:
    if not _DP_CALL_RE.search(text):
        return None
    literal_remainder = _DP_CALL_RE.sub("", text).strip()
    if not literal_remainder:
        return None
    out: list[str] = []
    last = 0
    for match in _DP_CALL_RE.finditer(text):
        next_char = text[match.end() : match.end() + 1]
        if next_char in {".", "[", "&"}:
            return None
        out.append(text[last : match.start()])
        value = resolve_dp_json(match.group(1), ctx, state)
        out.append("" if value is MISSING else str(value))
        last = match.end()
    out.append(text[last:])
    return "".join(out)


def quote_sql_literal(value: Any) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def formula_condition(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return present(value)


def strip_wrapping_parens(text: str) -> str:
    while text.startswith("(") and text.endswith(")") and wraps_entire_expression(text):
        text = text[1:-1].strip()
    return text


def wraps_entire_expression(text: str) -> bool:
    quote: str | None = None
    escaped = False
    depth = 0
    for idx, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "(":
            depth += 1
            continue
        if char == ")":
            depth -= 1
            if depth == 0:
                return idx == len(text) - 1
    return False


def decode_workato_string(value: str) -> str:
    out: list[str] = []
    idx = 0
    while idx < len(value):
        char = value[idx]
        if char == "\\" and idx + 1 < len(value):
            nxt = value[idx + 1]
            if nxt == "n":
                out.append("\n")
            elif nxt == "t":
                out.append("\t")
            elif nxt == "r":
                out.append("\r")
            elif nxt in {'"', "\\", "%"}:
                # Ruby double-quoted semantics: an escaped punctuation char is
                # the char itself ("\%" == "%"; 113983745 gsub(" ","\%") builds
                # a SOQL wildcard). Only '%' is admitted here — other unknown
                # escapes in the corpus (\s, \d, \*) live in regex-literal
                # contexts that must keep their backslashes; widen only with
                # a verified failing case.
                out.append(nxt)
            else:
                out.append("\\" + nxt)
            idx += 2
            continue
        out.append(char)
        idx += 1
    return "".join(out)


def split_top_level_ternary(text: str) -> tuple[str, str, str] | None:
    question = find_top_level_token(text, "?")
    if question == -1:
        return None
    colon = find_top_level_token(text[question + 1:], ":")
    if colon == -1:
        return None
    colon += question + 1
    return text[:question].strip(), text[question + 1:colon].strip(), text[colon + 1:].strip()


def matching_bracket_index(text: str) -> int:
    """Index of the `]` matching a leading `[`, honoring quotes/escapes; -1 if
    unbalanced or the text does not start with `[`."""
    if not text.startswith("["):
        return -1
    quote: str | None = None
    escaped = False
    depth = 0
    for idx, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return idx
    return -1


def split_top_level(text: str, token: str) -> list[str]:
    parts: list[str] = []
    start = 0
    idx = find_top_level_token(text, token)
    while idx != -1:
        parts.append(text[start:idx].strip())
        start = idx + len(token)
        next_idx = find_top_level_token(text[start:], token)
        idx = -1 if next_idx == -1 else start + next_idx
    if parts:
        parts.append(text[start:].strip())
    return parts or [text.strip()]


def find_top_level_token(text: str, token: str) -> int:
    quote: str | None = None
    escaped = False
    paren = 0
    slash_regex = False
    idx = 0
    while idx < len(text):
        char = text[idx]
        if escaped:
            escaped = False
            idx += 1
            continue
        if char == "\\":
            escaped = True
            idx += 1
            continue
        if quote:
            if char == quote:
                quote = None
            idx += 1
            continue
        if slash_regex:
            if char == "/":
                slash_regex = False
            idx += 1
            continue
        if char in {"'", '"'}:
            quote = char
            idx += 1
            continue
        if char == "/" and idx > 0 and text[idx - 1] == "(":
            slash_regex = True
            idx += 1
            continue
        if char == "(":
            paren += 1
            idx += 1
            continue
        if char == ")":
            paren = max(0, paren - 1)
            idx += 1
            continue
        if (
            token == "?"
            and char == "?"
            and idx > 0
            and (text[idx - 1].isalnum() or text[idx - 1] == "_")
        ):
            idx += 1
            continue
        if paren == 0 and text.startswith(token, idx):
            return idx
        idx += 1
    return -1


def split_presence_or(text: str) -> tuple[str, str] | None:
    """Split `<lhs>.presence or <rhs>` at a TOP-LEVEL marker only. A marker
    inside parentheses (e.g. `(a.presence or b.presence) > 100`) must NOT
    split here — splitting mid-expression rendered garbage like `'((' + '500'`
    without raising; such texts fall through to the arithmetic engine, which
    handles parenthesized presence-or correctly."""
    marker = ".presence or "
    idx = find_top_level_token(text, marker)
    if idx == -1:
        return None
    return text[:idx], text[idx + len(marker):]


def _parse_if_formula_node(
    lines: list[str], idx: int
) -> tuple[tuple[Any, ...], int]:
    if idx >= len(lines):
        return ("expr", '""'), idx
    line = lines[idx]
    if line.startswith("if "):
        return _parse_if_formula_chain(lines, idx)
    return ("expr", line), idx + 1


def _parse_if_formula_chain(
    lines: list[str], idx: int
) -> tuple[tuple[Any, ...], int]:
    line = lines[idx]
    if not (line.startswith("if ") or line.startswith("elsif ")):
        raise NonRecipeError(f"expected if/elsif formula line, got: {line}")
    condition = line.split(" ", 1)[1].strip()
    then_node, cursor = _parse_if_formula_node(lines, idx + 1)
    if cursor >= len(lines):
        raise NonRecipeError(f"if formula missing end near: {line}")
    delimiter = lines[cursor]
    if delimiter.startswith("elsif "):
        else_node, consumed = _parse_if_formula_chain(lines, cursor)
        return ("if", condition, then_node, else_node), consumed
    if delimiter == "else":
        else_node, cursor = _parse_if_formula_node(lines, cursor + 1)
    elif delimiter.startswith("else "):
        else_node = ("expr", delimiter.split(" ", 1)[1].strip() or '""')
        cursor += 1
    elif delimiter == "end":
        return ("if", condition, then_node, ("expr", '""')), cursor + 1
    else:
        raise NonRecipeError(f"if formula requires else/end near: {delimiter}")
    if cursor >= len(lines) or lines[cursor] != "end":
        raise NonRecipeError(f"if formula missing end near: {line}")
    return ("if", condition, then_node, else_node), cursor + 1


def _eval_if_formula_node(
    node: tuple[Any, ...], ctx: RecipeContext, state: RuntimeState
) -> Any:
    if node[0] == "expr":
        return eval_formula("=" + str(node[1]), ctx, state)
    _kind, condition, then_node, else_node = node
    matched = formula_condition(eval_formula("=" + str(condition), ctx, state))
    return _eval_if_formula_node(
        then_node if matched else else_node,
        ctx,
        state,
    )


def eval_if_formula(text: str, ctx: RecipeContext, state: RuntimeState) -> Any:
    """Evaluate nested line-oriented Ruby if/elsif/else expressions."""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    node, consumed = _parse_if_formula_node(lines, 0)
    if consumed != len(lines):
        raise NonRecipeError(f"if formula has trailing lines: {lines[consumed:]}")
    return _eval_if_formula_node(node, ctx, state)


def data_path(path: str, state: RuntimeState) -> Any:
    parts = path.split(".")
    if len(parts) < 3 or parts[0] != "data":
        return MISSING
    provider, line = parts[1], parts[2]
    if line == state.trigger_as and provider == state.trigger_provider:
        root = state.trigger
    else:
        root = state.data.get(provider, {}).get(line, MISSING)
        if root is MISSING:
            root = state.steps.get(line, MISSING)
    value = lookup_path(root, parts[3:])
    if (
        value is MISSING
        and provider == "foreach"
        and len(parts) == 4
        and parts[3] in {"index", "seq_no", "size"}
    ):
        # Loop counters live in foreach_meta, not on the current item
        # (e.g. plain _('data.foreach.<line>.seq_no')).
        meta = state.foreach_meta.get(line)
        if isinstance(meta, dict) and parts[3] in meta:
            return meta[parts[3]]
    return value


def compare_formula_value(value: Any) -> str:
    return "" if value is MISSING else str(value)


def lookup_path(root: Any, path: list[Any]) -> Any:
    if root is MISSING:
        # Unknown pill SOURCE (step never ran / unseeded provider line): keep
        # the MISSING sentinel so unknown-source pills stay fail-fast at the
        # surfaces that check it (db filters, adapter arg guards, foreach
        # sources) and render "" in condition slots (live-evidenced 130992107).
        return MISSING
    current = root
    for raw_part in path:
        if current is MISSING or current is None:
            # Workato/Ruby datapill nil-PROPAGATION: the source exists but a
            # prior segment resolved to nil/absent (e.g. first-record deref of
            # an empty records list) and the path walks on THROUGH it — the
            # pill is nil, silently; never an unknown-pill error. Only a LEAF
            # miss keeps the MISSING sentinel (pre-existing render/"" and
            # foreach-counter fallback semantics). Validated by a full
            # offline trace-replay probe over all recorded variants
            # (2026-07-14 nil-propagation pass; closed 95840865's 404 arm).
            return None
        if isinstance(raw_part, dict):
            typ = raw_part.get("path_element_type")
            if typ == "size":
                current = len(as_list(current))
                continue
            if typ == "current_item":
                seq = as_list(current)
                current = seq[0] if seq else MISSING
                continue
            if typ == "join":
                # Related-record pill (e.g. get_custom_object over Account__c):
                # walk into the expanded parent dict that relationship_expansion
                # attached. A populated FK without expansion data is a harness
                # gap and must fail loudly, never render null.
                src_key = str(raw_part.get("src_key") or "")
                row = current if isinstance(current, dict) else (as_list(current)[0] if as_list(current) else MISSING)
                if row is MISSING:
                    # first-record deref of an empty list: nil propagation.
                    return None
                if not isinstance(row, dict):
                    return MISSING
                fk_value = row.get(src_key)
                candidates = [src_key[:-3] + "__r", src_key[:-3]] if src_key.endswith("__c") else [src_key.removesuffix("Id")]
                parent = next((row[name] for name in candidates if isinstance(row.get(name), dict)), MISSING)
                if parent is MISSING:
                    if fk_value in (None, "", MISSING):
                        # nil FK: the related record is nil (nil propagation).
                        return None
                    raise NonRecipeError(
                        f"join datapill over {src_key} has a live id but no expanded parent record; "
                        "seed salesforce.relationship_expansion: true"
                    )
                current = parent
                continue
            raw_part = typ
        part = raw_part
        if isinstance(current, dict) and part in {"first", "last"} and part not in current:
            seq = as_list(current)
            current = (seq[0] if part == "first" else seq[-1]) if seq else MISSING
            continue
        if isinstance(current, dict):
            if part in current:
                current = current[part]
            elif "fields" in current and isinstance(current["fields"], dict) and part in current["fields"]:
                current = current["fields"][part]
            elif "entry" in current and isinstance(current["entry"], dict) and part in current["entry"]:
                current = current["entry"][part]
            elif "result" in current and isinstance(current["result"], dict) and part in current["result"]:
                current = current["result"][part]
            elif part in {"entries", "records", "rows"}:
                current = current.get(part, [])
            else:
                # Workato disambiguates repeated pill labels with a trailing
                # _<8-hex> suffix (e.g. number_of_columns_1d38290b); live rows
                # carry the bare column name. Only for that suffixed form,
                # strip and retry case-insensitively (Snowflake uppercases
                # identifiers). Plain misses stay MISSING as before.
                suffix = re.fullmatch(r"(.+)_[0-9a-f]{8}", str(part))
                if suffix:
                    lower_map = {str(key).lower(): key for key in current}
                    key = lower_map.get(suffix.group(1).lower())
                    if key is None:
                        key = lower_map.get(str(part).lower())
                    current = current[key] if key is not None else MISSING
                else:
                    current = MISSING
            continue
        if isinstance(current, list):
            if part in {"first", "current_item"}:
                current = current[0] if current else MISSING
            elif part == "size":
                current = len(current)
            elif isinstance(part, int) or str(part).isdigit():
                idx = int(part)
                current = current[idx] if 0 <= idx < len(current) else MISSING
            else:
                current = field_value(current[0], str(part)) if current else MISSING
            continue
        return MISSING
    return current


def as_list(value: Any) -> list[Any]:
    if value is MISSING or value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("entries", "records", "rows"):
            if isinstance(value.get(key), list):
                return value[key]
    return [value]


def variable_target(raw_name: Any) -> tuple[str, str]:
    if raw_name in (None, ""):
        return "", ""
    parts = str(raw_name).split(":")
    if len(parts) < 2:
        raise RawRecipeExecutionError(f"invalid Workato variable target name: {raw_name}")
    target_step = parts[1]
    target_field = parts[2] if len(parts) > 2 else ""
    return target_step, target_field


def update_variable_list(
    state: RuntimeState,
    target_step: str,
    target_field: str,
    values: list[Any],
) -> dict[str, Any]:
    if not target_step:
        raise RawRecipeExecutionError("Workato list update is missing target step")
    target = state.steps.setdefault(target_step, {})
    if not isinstance(target, dict):
        raise RawRecipeExecutionError(f"list target step is not an object: {target_step}")
    provider_target = state.data.setdefault("workato_variable", {}).setdefault(target_step, target)
    if not isinstance(provider_target, dict):
        raise RawRecipeExecutionError(f"list provider target is not an object: {target_step}")
    list_key = target_field
    if not list_key:
        list_keys = [key for key, value in target.items() if isinstance(value, list)]
        if not list_keys:
            raise RawRecipeExecutionError(f"list target step has no list value: {target_step}")
        list_key = "list_items" if "list_items" in list_keys else str(list_keys[0])
    current = target.setdefault(list_key, [])
    if not isinstance(current, list):
        raise RawRecipeExecutionError(f"target variable is not a list: {target_step}.{list_key}")
    current.extend(values)
    provider_target[list_key] = current
    if not target_field:
        for key, value in list(target.items()):
            if isinstance(value, list):
                target[key] = current
                provider_target[key] = current
    return {list_key: list(current)}


def field_value(row: Any, field: str) -> Any:
    if isinstance(row, dict):
        if field in row:
            return row[field]
        fields = row.get("fields")
        if isinstance(fields, dict):
            if field in fields:
                return fields[field]
            lower = str(field).lower()
            for key, value in fields.items():
                if str(key).lower() == lower:
                    return value
        lower = str(field).lower()
        for key, value in row.items():
            if str(key).lower() == lower:
                return value
    return None


def present(value: Any) -> bool:
    return value not in (None, "", MISSING, [], {})


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def compare_condition_values(lhs: Any, rhs: Any) -> int:
    if lhs is MISSING or rhs is MISSING:
        raise RawRecipeExecutionError("cannot compare missing condition values")
    try:
        left = Decimal(str(lhs))
        right = Decimal(str(rhs))
    except (InvalidOperation, ValueError):
        # Non-numeric operands (including "") compare as strings, matching
        # Workato: "" > '0' is false, not a job error.
        left_text = str(lhs)
        right_text = str(rhs)
        return (left_text > right_text) - (left_text < right_text)
    return (left > right) - (left < right)


def plus_days_to_date(value: Any, days: int) -> str:
    text = str(value or "")
    if "T" in text:
        dt = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
        return (dt + datetime.timedelta(days=days)).date().isoformat()
    return (datetime.date.fromisoformat(text) + datetime.timedelta(days=days)).isoformat()


def _shift_date_duration(base: Any, amount: int, unit: str) -> str | None:
    """Add a duration to a date/datetime string. Returns None if base is not a
    parseable date (so callers fall through to normal formula handling)."""
    text = str(base).strip()
    if not text:
        return None
    try:
        if "T" in text or " " in text:
            dt = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
            date_only = False
        else:
            dt = datetime.datetime.fromisoformat(text)
            date_only = True
    except ValueError:
        return None
    if unit.startswith("day"):
        res = dt + datetime.timedelta(days=amount)
    elif unit.startswith("week"):
        res = dt + datetime.timedelta(weeks=amount)
    elif unit.startswith("month"):
        res = shift_months(dt, amount)
    else:  # year(s)
        res = shift_months(dt, amount * 12)
    return res.date().isoformat() if date_only else res.isoformat()


def shift_months(dt: datetime.datetime, months: int) -> datetime.datetime:
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)
    last_day = (next_month - datetime.timedelta(days=1)).day
    return dt.replace(year=year, month=month, day=min(dt.day, last_day))


def workato_to_date(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    if "T" in text:
        return datetime.datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    return datetime.date.fromisoformat(text[:10]).isoformat()


def strftime_workato(value: Any, fmt: str) -> str:
    if value is None or value is MISSING:
        # Ruby: nil.strftime is NoMethodError (job error). Guarded here so a
        # nil receiver fails loudly as a recipe error instead of the raw
        # ValueError the ISO parser raised on the rendered string "None".
        # (nil under `&.strftime` short-circuits in apply_dp_methods and
        # never reaches this.)
        raise RawRecipeExecutionError(".strftime on a missing datapill value")
    try:
        dt = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise RawRecipeExecutionError(f".strftime on a non-datetime value: {value!r}") from exc
    dt = dt.astimezone(datetime.timezone.utc)
    return render_strftime(dt, fmt)


def strftime_seed_now_in_zone(ctx: RecipeContext, tz_name: str, fmt: str) -> str:
    if "now" not in ctx.seed or ctx.seed.get("now") in (None, ""):
        raise RawRecipeExecutionError("formula 'now' requires a fixed seed['now']")
    dt = datetime.datetime.fromisoformat(str(ctx.seed["now"]).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise RawRecipeExecutionError("formula 'now' requires seed['now'] to include timezone information")
    local_dt = dt.astimezone(resolve_zone_info(tz_name))
    return render_strftime(local_dt, fmt)


def seed_today(ctx: RecipeContext) -> datetime.date:
    if "now" not in ctx.seed or ctx.seed.get("now") in (None, ""):
        raise RawRecipeExecutionError("formula 'today' requires a fixed seed['now']")
    dt = datetime.datetime.fromisoformat(str(ctx.seed["now"]).replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        dt = dt.astimezone(datetime.timezone.utc)
    return dt.date()


def _seed_now_dt(ctx: RecipeContext) -> datetime.datetime:
    if "now" not in ctx.seed or ctx.seed.get("now") in (None, ""):
        raise RawRecipeExecutionError("formula 'now' requires a fixed seed['now']")
    dt = datetime.datetime.fromisoformat(str(ctx.seed["now"]).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise RawRecipeExecutionError("formula 'now' requires seed['now'] to include timezone information")
    return dt


def resolve_data_call(path: str, meta_kind: str, state: RuntimeState) -> Any:
    """Resolve an underscore data-call with an explicit source kind. For
    'foreach_meta' the loop metadata (index/seq_no/size) is consulted first,
    falling back to the ordinary data path; all other kinds resolve normally."""
    if (meta_kind or "").strip() == "foreach_meta":
        value = foreach_meta_value(path, state)
        if value is not MISSING:
            return value
    if (meta_kind or "").strip() == "list_meta":
        value = data_path(path, state)
        if value is not MISSING and value is not None:
            return value
        # Rows materialized by query_list carry no ____Size/____Index
        # placeholders (unlike create_list's size form) — derive from the
        # underlying list; a missing list stays MISSING. A None value here is
        # a nil-PROPAGATED path (e.g. list.first.____Size over an empty list):
        # ____Size/____Index are harness list METADATA, so the derivation
        # below must still fire (size of an empty list is 0, not nil).
        parts = str(path).split(".")
        if parts and parts[-1] in {"____Size", "____Index"}:
            field = parts.pop()
            position = parts.pop() if parts and parts[-1] in {"first", "last"} else "first"
            seq = data_path(".".join(parts), state)
            if seq is not MISSING:
                items = as_list(seq)
                if field == "____Size":
                    return len(items)
                return 0 if position == "first" else max(0, len(items) - 1)
        return MISSING
    return data_path(path, state)


def foreach_meta_value(path: str, state: RuntimeState) -> Any:
    parts = str(path).split(".")
    # Expect data.foreach.<line>.<field> (field is index / seq_no / size).
    if len(parts) >= 4 and parts[0] == "data" and parts[1] == "foreach":
        meta = state.foreach_meta.get(parts[2], {})
        if parts[3] in meta:
            return meta[parts[3]]
    return MISSING


def _extract_paren(text: str, open_idx: int) -> tuple[str, int]:
    """Given text with an opening '(' at open_idx, return (inner, end) where
    inner is the balanced content and end is the index just past the matching
    ')'. Quotes (single/double) are respected so parens inside string literals
    do not affect the balance."""
    depth = 0
    quote: str | None = None
    escaped = False
    idx = open_idx
    while idx < len(text):
        char = text[idx]
        if escaped:
            escaped = False
            idx += 1
            continue
        if char == "\\":
            escaped = True
            idx += 1
            continue
        if quote:
            if char == quote:
                quote = None
            idx += 1
            continue
        if char in {"'", '"'}:
            quote = char
            idx += 1
            continue
        if char == "(":
            depth += 1
            idx += 1
            continue
        if char == ")":
            depth -= 1
            idx += 1
            if depth == 0:
                return text[open_idx + 1: idx - 1], idx
            continue
        idx += 1
    raise RawRecipeExecutionError(f"unbalanced parentheses in formula: {text}")


def eval_lookup_expr(text: str, ctx: RecipeContext, state: RuntimeState) -> Any:
    """Evaluate a Workato lookup() formula, e.g.
        lookup("<table name>", <Col>: <value>)["<field>"]
        (lookup("<t>", "Country": _('...'))["Region"]).split(",")[0].to_i
    The table is resolved by name against the seeded lookup tables (via the
    lookup_table.get_entry tool, which understands name aliases). Returns the
    matched row's field, or MISSING (-> null) when there is no matching row."""
    stripped = text.strip()
    call_pos = stripped.index("lookup")
    prefix = stripped[:call_pos].strip()
    open_idx = stripped.index("(", call_pos)
    args_str, after = _extract_paren(stripped, open_idx)
    arg_parts = split_top_level(args_str, ",")
    if len(arg_parts) < 2:
        raise NonRecipeError(f"unsupported lookup() formula: ={text}")
    table_name = _strip_quotes(arg_parts[0].strip())
    pair = ",".join(arg_parts[1:]).strip()
    colon = find_top_level_token(pair, ":")
    if colon == -1:
        raise NonRecipeError(f"unsupported lookup() formula (no key): ={text}")
    key = _strip_quotes(pair[:colon].strip())
    value_expr = pair[colon + 1:].strip()
    match_value = eval_formula("=" + value_expr, ctx, state)

    rest = stripped[after:].lstrip()
    field_match = re.match(r'\[\s*"((?:\\.|[^"])*)"\s*\]', rest)
    single_quoted = False
    if not field_match:
        field_match = re.match(r"\[\s*'((?:\\.|[^'])*)'\s*\]", rest)
        single_quoted = True
    if not field_match:
        raise NonRecipeError(f"unsupported lookup() formula (no field index): ={text}")
    field = (
        field_match.group(1).replace("\\'", "'")
        if single_quoted
        else decode_workato_string(field_match.group(1))
    )
    rest = rest[field_match.end():]
    if prefix == "(":
        rest = rest.lstrip()
        if rest.startswith(")"):
            rest = rest[1:]

    row = eval_lookup_row(table_name, key, match_value, ctx)
    value_out: Any = row[field] if (isinstance(row, dict) and field in row) else MISSING
    if rest.strip():
        return apply_dp_methods(value_out, rest, ctx, state)
    return value_out


def eval_lookup_row(table_name: str, key: str, value: Any, ctx: RecipeContext) -> dict[str, Any]:
    if value is MISSING or value is None:
        return {}
    result = ctx.tools.call(
        "lookup_table.get_entry",
        {"lookup_table_id": table_name, "parameters": {key: value}},
    )
    entry = result.get("entry") if isinstance(result, dict) else None
    return entry if isinstance(entry, dict) else {}


def _strip_quotes(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and ((text[0] == '"' and text[-1] == '"') or (text[0] == "'" and text[-1] == "'")):
        body = text[1:-1]
        return decode_workato_string(body) if text[0] == '"' else body.replace("\\'", "'")
    return text


def render_strftime(dt: datetime.datetime, fmt: str) -> str:
    marker = "__WORKATO_BLANK_PADDED_HOUR__"
    millis_marker = "__WORKATO_MILLIS__"
    rendered = dt.strftime(fmt.replace("%k", marker).replace("%L", millis_marker))
    rendered = rendered.replace(millis_marker, f"{dt.microsecond // 1000:03d}")
    return rendered.replace(marker, f"{dt.hour:2d}")


def decimal_sum(values: list[Any]) -> str:
    total = Decimal("0")
    for value in values:
        if value in (None, "", MISSING):
            raise RawRecipeExecutionError("nil/blank value in numeric sum")
        try:
            total += Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise RawRecipeExecutionError(f"non-numeric value in numeric sum: {value!r}") from exc
    if total == total.to_integral_value():
        return str(total.quantize(Decimal("1")))
    return format(total.normalize(), "f").rstrip("0").rstrip(".")


def count_actions(nodes: list[Any]) -> int:
    total = 0
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if node.get("keyword") == "action" and not node.get("skip"):
            total += 1
        total += count_actions(node.get("block") or [])
    return total


def step_key(node: dict[str, Any], default_index: int) -> str:
    return str(node.get("as") or node.get("number") or default_index + 1)


def trace_base(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "number": node.get("number"),
        "as": node.get("as"),
        "keyword": node.get("keyword"),
        "provider": node.get("provider"),
        "name": node.get("name"),
    }
