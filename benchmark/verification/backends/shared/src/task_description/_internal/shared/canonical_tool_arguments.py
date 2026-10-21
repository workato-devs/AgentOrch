"""Canonical benchmark argument projection for raw recipe actions.

The raw recipe is the sole static workflow authority.  This module contains
the deterministic adapter from connector-authoring arguments to the
benchmark-visible argument shape.  It is deliberately independent of task
description rendering so ground-truth compilation cannot silently inherit
documentation-only redaction or prompt behavior.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any


DYNAMIC_ARGUMENT_VALUE = "<value described by Q or returned by a prior tool>"
_DATAPILL_INTERPOLATION_RE = re.compile(
    r"#\{_dp\('.*?'\)\}",
    flags=re.S,
)
WORKATO_DB_WRITE_TOOLS = {
    "workato_db_table.add_record",
    "workato_db_table.update_record",
    "workato_db_table.upsert_record",
}


def _sql_has_top_level_order_by(sql: str) -> bool:
    """Return true only for an ORDER BY outside parentheses/SQL strings."""

    text = str(sql)
    depth = 0
    quote = False
    index = 0
    while index < len(text):
        char = text[index]
        if quote:
            if char == "'":
                quote = False
            index += 1
            continue
        if char == "'":
            quote = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif (
            depth == 0
            and re.match(r"ORDER\s+BY\b", text[index:], flags=re.I)
            and (
                index == 0
                or not (text[index - 1].isalnum() or text[index - 1] == "_")
            )
        ):
            return True
        index += 1
    return False

# A projection is ``exact`` only when its output shape is determined by the
# recipe action itself.  ``runtime_dependent`` means RawWorkatoRuntime adds or
# rewrites an argument from hidden episode state, so no frozen recipe-level
# projection can equal every runtime call without changing that interface.
# Keep this registry next to the adapters: the coverage report imports it and
# fails closed for tools which have silently fallen through to raw authoring
# input.
EXACT_STATIC_PROJECTION_TOOLS = frozenset(
    {
        "clock.wait_for_interval",
        "google_sheets.add_spreadsheet_row_v4",
        "google_sheets.get_spreadsheet_rows_v4",
        "google_sheets.search_spreadsheet_rows_v4_new",
        "google_sheets.update_row_v4_new",
        "google_drive.create_folder",
        "jira.create_issue",
        "logger.log_message",
        "lookup_table.add_entry",
        "lookup_table.add_batch_of_entries",
        "lookup_table.delete_entry",
        "lookup_table.get_entries",
        "lookup_table.get_entry",
        "lookup_table.search_entries",
        "lookup_table.truncate",
        "lookup_table.update_entry",
        "salesforce.create_record",
        "salesforce.search_records",
        "salesforce.update_record",
        "salesforce.upsert_record",
        "slack.update_blocks_by_block_id",
        "slack_bot.get_user_by_email",
        "slack_bot.generate_menu_options",
        "slack_bot.open_bot_app_home",
        "snowflake.run_custom_sql",
        "snowflake.search_rows",
        "snowflake.search_rows_sql",
        "snowflake.update_rows",
        "snowflake.upsert_rows_batch",
        "workato_api_platform.return_response",
        "workato_app.get_recipe",
        "workato_app.list_jobs",
        "workato_app.rerun_jobs",
        "workato_app.start_recipe",
        "workato_app.stop_recipe",
        "workato_db_table.add_record",
        "workato_db_table.delete_record",
        "workato_db_table.get_records",
        "workato_db_table.truncate_table",
        "workato_db_table.update_record",
        "workato_db_table.upsert_record",
        "workato_genie.workflow_return_result",
        "workato_pub_sub.publish_to_topic",
        "workato_pub_sub.publish_to_topic_batch",
        "workato_recipe_function.return_result",
        "workato_runtime.accumulate_list_items",
        "workato_runtime.declare_list",
        "workato_runtime.declare_variable",
        "workato_runtime.insert_to_list",
        "workato_runtime.insert_to_list_batch",
        "workato_runtime.log_message",
        "workato_runtime.parse_json",
        "workato_runtime.create_list",
        "workato_runtime.update_variable",
        "workato_runtime.update_variables",
        "workato_service.call_service_async",
        "workato_service.call_service",
        "workato_service.send_reply",
        "workato_smart_list.create_list",
        "workato_smart_list.create_list_from_csv",
        "workato_smart_list.query_list",
    }
)

RUNTIME_DEPENDENT_PROJECTION_TOOLS = frozenset(
    {
        # Channel overrides and trigger/message seed data are folded into the
        # actual call by RawWorkatoRuntime.
        "slack.post_message",
        "slack.post_reply",
        "salesforce.composite_update_sobject",
        "salesforce.search_sobjects_soql_bulk_csv_v2",
    }
)


def projection_support(
    tool: str,
    source_tool: str | None = None,
    arguments: dict[str, Any] | None = None,
) -> str:
    """Return the fail-closed static projection support classification."""

    raw_tool = source_tool or tool
    if raw_tool in RUNTIME_DEPENDENT_PROJECTION_TOOLS:
        return "runtime_dependent"
    if tool in EXACT_STATIC_PROJECTION_TOOLS:
        return "exact"
    if tool in RUNTIME_DEPENDENT_PROJECTION_TOOLS:
        return "runtime_dependent"
    return "unsupported"


def public_configured_argument(value: Any) -> Any:
    """Expose configured literals while replacing private datapill syntax."""

    if isinstance(value, dict):
        return {
            str(key): public_configured_argument(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [public_configured_argument(item) for item in value]
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    formula_literals = {
        "=null": None,
        "=true": True,
        "=false": False,
    }
    if stripped.lower() in formula_literals:
        return formula_literals[stripped.lower()]
    interpolated = _DATAPILL_INTERPOLATION_RE.sub(
        DYNAMIC_ARGUMENT_VALUE,
        value,
    )
    if (
        interpolated != value
        and "_dp(" not in interpolated
        and "#{" not in interpolated
        and not stripped.startswith("=")
    ):
        return interpolated
    if "_dp(" in value or "#{" in value or stripped.startswith("="):
        return DYNAMIC_ARGUMENT_VALUE
    return value


def input_field_key_map(
    schema: Any,
    path: tuple[str, ...] = (),
    tool: str = "",
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if not isinstance(schema, list):
        return result
    for field in schema:
        if not isinstance(field, dict):
            continue
        key = str(field.get("name") or "")
        if not key:
            continue
        if tool in WORKATO_DB_WRITE_TOOLS and not path and key == "parameters":
            key = "record"
        if tool.startswith("workato_db_table."):
            key = key.replace("-", "_")
        field_path = (*path, key)
        result.append(
            {
                "path": list(field_path),
                "key": key,
                "label": str(field.get("label") or key),
                "type": field.get("type"),
                "required": field.get("optional") is False,
            }
        )
        result.extend(
            input_field_key_map(
                field.get("properties") or [],
                field_path,
                tool,
            )
        )
    return result


def canonical_datatable_filter(
    raw_filter: Any,
    *,
    redact_dynamic_values: bool = True,
) -> Any:
    normalize = public_configured_argument if redact_dynamic_values else deepcopy
    if not isinstance(raw_filter, dict):
        return normalize(raw_filter)
    field_id = str(raw_filter.get("field_id") or "").replace("-", "_")
    # Match RawRecipeExecutor's connector semantics exactly. Workato exports
    # several editor-type alternatives in one filter row; the runtime picks
    # the first configured value in this fixed order, not whichever key
    # happens to appear first in JSON.
    value_operator_pairs = (
        ("value", "op"),
        ("value_default", "op_default"),
        ("value_relation", "op_relation"),
        ("value_integer", "op_integer"),
        ("value_date_time", "op_date_time"),
        ("value_date", "op_date"),
    )
    value_key: str | None = None
    operator_key: str | None = None
    for candidate_value, candidate_operator in value_operator_pairs:
        if raw_filter.get(candidate_value) is not None:
            value_key = candidate_value
            operator_key = candidate_operator
            break
    boolean_operator = str(raw_filter.get("op_boolean") or "").lower()
    if value_key is None and boolean_operator in {"istrue", "isfalse"}:
        return {
            "field_id": field_id,
            "op": "eq",
            "value": boolean_operator == "istrue",
        }
    if value_key is None:
        operator_key = next(
            (
                candidate_operator
                for _, candidate_operator in value_operator_pairs
                if raw_filter.get(candidate_operator) not in (None, "")
            ),
            None,
        )
    raw_operator = str(
        (raw_filter.get(operator_key) or "eq") if operator_key else "eq"
    ).lower()
    if raw_operator == "equals":
        raw_operator = "eq"
    if raw_operator in {"istrue", "isfalse"}:
        return {
            "field_id": field_id,
            "op": "eq",
            "value": raw_operator == "istrue",
        }
    result: dict[str, Any] = {
        "field_id": field_id,
        "op": raw_operator,
    }
    # Real exports may pair ``op_id`` with ``value_default``.  Select an
    # actually present value field; never synthesize a missing key and
    # silently replace a recipe datapill with None. Presence operators ignore
    # the value semantically, but the raw executor retains any explicitly
    # configured value in the benchmark-visible call, so exact trace fidelity
    # retains it as well.
    raw_value = raw_filter.get(value_key) if value_key is not None else None
    if (
        isinstance(raw_value, str)
        and raw_value.startswith("<anon>")
        and raw_value.endswith("</anon>")
    ):
        raw_value = raw_value[len("<anon>") : -len("</anon>")]
    result["value"] = normalize(raw_value)
    return result


def _parameter_data(arguments: dict[str, Any]) -> dict[str, Any]:
    parameters = arguments.get("parameters")
    return deepcopy(parameters) if isinstance(parameters, dict) else {}


def _workato_db_primary_field_id(
    arguments: dict[str, Any],
    input_schema: Any,
    source_node: dict[str, Any] | None,
) -> Any:
    configured = arguments.get("primary_field_id")
    if configured and not str(configured).startswith("<anon>"):
        return configured
    source_node = source_node if isinstance(source_node, dict) else {}
    selection = (
        source_node.get("dynamic_pick_list_selection")
        or source_node.get("dynamicPickListSelection")
        or {}
    )
    label = str(
        selection.get("primary_field_id")
        if isinstance(selection, dict)
        else ""
    ).strip().casefold()
    if not label:
        return configured
    schemas = (
        source_node.get("extended_input_schema")
        or source_node.get("extendedInputSchema")
        or input_schema
        or []
    )
    record = _parameter_data(arguments)
    for schema in schemas if isinstance(schemas, list) else []:
        if not isinstance(schema, dict) or schema.get("name") != "parameters":
            continue
        for field in schema.get("properties") or []:
            if not isinstance(field, dict):
                continue
            name = str(field.get("name") or "")
            if (
                name in record
                and str(field.get("label") or "").strip().casefold() == label
            ):
                return name
    return configured


def _snowflake_parameters(arguments: dict[str, Any]) -> dict[str, Any]:
    parameters = arguments.get("parameters")
    if not isinstance(parameters, dict):
        return {}
    data = parameters.get("data")
    return deepcopy(data) if isinstance(data, dict) else {}


def _field_labels(input_schema: Any, container: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    if not isinstance(input_schema, list):
        return labels
    for field in input_schema:
        if not isinstance(field, dict) or field.get("name") != container:
            continue
        for prop in field.get("properties") or []:
            if not isinstance(prop, dict):
                continue
            key = str(prop.get("name") or "")
            label = str(prop.get("label") or "")
            if key and label:
                labels[key] = label
    return labels


def _sheet_data(value: Any, labels: dict[str, str]) -> Any:
    if not isinstance(value, dict):
        return deepcopy(value)
    result: dict[str, Any] = {}
    # Workato submits sheet columns in connector-schema order. Stage-1 JSON
    # canonicalization sorts object keys lexically (col_1, col_10, col_2), so
    # iterating the argument object would corrupt the exact header order.
    # Reconstruct configured columns from the authoritative schema first,
    # then retain schema-less extras in their original order.
    ordered_keys = [key for key in labels if key in value]
    ordered_keys.extend(key for key in value if key not in labels)
    for key in ordered_keys:
        item = value[key]
        header = labels.get(str(key), str(key))
        if header.startswith("col_"):
            header = header[4:]
        result[header] = item
    return result


def _salesforce_sobject_from_query(query: Any) -> str:
    if not isinstance(query, str):
        return ""
    match = re.search(r"\bFROM\s+([A-Za-z0-9_]+)", query, flags=re.I)
    return match.group(1) if match else ""


def _truthy_literal(value: Any) -> Any:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return value


def _canonical_optional_int(value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return value


def _schema_convert(value: Any, input_schema: Any, field_name: str) -> Any:
    if not isinstance(input_schema, list):
        return value
    field = next(
        (
            row
            for row in input_schema
            if isinstance(row, dict) and row.get("name") == field_name
        ),
        None,
    )
    if not isinstance(field, dict):
        return value

    def convert(candidate: Any, schema: dict[str, Any]) -> Any:
        if schema.get("type") == "boolean":
            converted = _truthy_literal(candidate)
            if converted is candidate and not isinstance(candidate, bool):
                candidate = {"____canonical_schema_boolean": candidate}
            else:
                candidate = converted
        properties = schema.get("properties")
        if isinstance(candidate, dict) and isinstance(properties, list):
            by_name = {
                str(item.get("name")): item
                for item in properties
                if isinstance(item, dict) and item.get("name")
            }
            return {
                key: convert(item, by_name[key]) if key in by_name else item
                for key, item in candidate.items()
            }
        return candidate

    return convert(value, field)


def _snowflake_primary_keys(input_schema: Any) -> list[str]:
    keys: list[str] = []
    if not isinstance(input_schema, list):
        return keys
    for field in input_schema:
        if not isinstance(field, dict):
            continue
        for prop in field.get("properties") or []:
            if not isinstance(prop, dict):
                continue
            details = prop.get("details")
            if isinstance(details, dict) and details.get("primary_key") is True:
                key = details.get("column_name") or prop.get("name")
                if key:
                    keys.append(str(key))
    return keys


def _slack_configured_lines(arguments: dict[str, Any]) -> list[Any] | None:
    """Return recipe-configured message lines, or None for source expansion."""

    lines: list[Any] = []

    def visit_block(block: Any) -> bool:
        if not isinstance(block, dict):
            return True
        if "____source" in block:
            return False
        if block.get("section_text") not in (None, ""):
            lines.append(block.get("section_text"))
        for element in block.get("elements") or []:
            if isinstance(element, dict) and element.get("text") not in (None, ""):
                lines.append(element.get("text"))
        objects = block.get("objects")
        if isinstance(objects, dict):
            if "____source" in objects:
                return False
            children = objects.get("blocks")
            children = children if isinstance(children, list) else [children]
            for child in children:
                if child is not None and not visit_block(child):
                    return False
        return True

    for block in arguments.get("blocks") or []:
        if not visit_block(block):
            return None
    if arguments.get("text") not in (None, ""):
        lines.append(arguments.get("text"))
    message = arguments.get("message")
    message = message if isinstance(message, dict) else {}
    for key in ("pretext", "title", "attachment_text", "text"):
        if message.get(key) not in (None, ""):
            lines.append(message[key])
    for key in ("pretext", "title", "attachment_text"):
        if key not in message and arguments.get(key) not in (None, ""):
            lines.append(arguments[key])
    if "____source" in str(arguments.get("attachment_fields") or ""):
        return None
    for field in arguments.get("attachment_fields") or []:
        if not isinstance(field, dict):
            continue
        title = field.get("title") or ""
        value = field.get("value") or ""
        if title or value:
            lines.append(f"{title}: {value}")
    return lines


def _slack_text_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    def block_payload(block: Any) -> Any:
        if not isinstance(block, dict):
            return block
        result: dict[str, Any] = {}
        if "____source" in block:
            result["____source"] = deepcopy(block["____source"])
        if "section_text" in block:
            result["section_text"] = deepcopy(block["section_text"])
        elements = [
            {"text": deepcopy(element["text"])}
            for element in block.get("elements") or []
            if isinstance(element, dict) and "text" in element
        ]
        if elements:
            result["elements"] = elements
        objects = block.get("objects")
        if isinstance(objects, dict):
            projected_objects: dict[str, Any] = {}
            if "____source" in objects:
                projected_objects["____source"] = deepcopy(objects["____source"])
            children = objects.get("blocks")
            if isinstance(children, list):
                projected_objects["blocks"] = [
                    block_payload(child) for child in children
                ]
            elif children is not None:
                projected_objects["blocks"] = block_payload(children)
            if projected_objects:
                result["objects"] = projected_objects
        return result

    payload: dict[str, Any] = {}
    if arguments.get("blocks"):
        payload["blocks"] = [block_payload(item) for item in arguments["blocks"]]
    if "text" in arguments:
        payload["text"] = deepcopy(arguments["text"])
    message = arguments.get("message")
    if isinstance(message, dict):
        payload["message"] = {
            key: deepcopy(message[key])
            for key in ("pretext", "title", "attachment_text", "text")
            if key in message
        }
    for key in ("pretext", "title", "attachment_text"):
        if key in arguments:
            payload[key] = deepcopy(arguments[key])
    fields = arguments.get("attachment_fields")
    if isinstance(fields, dict):
        payload["attachment_fields"] = {
            key: deepcopy(fields[key])
            for key in ("____source", "title", "value")
            if key in fields
        }
    elif isinstance(fields, list):
        payload["attachment_fields"] = [
            {
                key: deepcopy(field[key])
                for key in ("title", "value")
                if key in field
            }
            for field in fields
            if isinstance(field, dict)
        ]
    return payload


def _slack_attachment_payload(
    arguments: dict[str, Any], *, executable: bool = False
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    message = arguments.get("message")
    if isinstance(message, dict):
        payload["message"] = {
            key: deepcopy(message[key])
            for key in (
                "color", "pretext", "title", "title_link",
                "attachment_text", "footer", "footer_icon",
            )
            if key in message
        }
    for key in (
        "color", "pretext", "title", "title_link", "attachment_text",
        "footer", "footer_icon", "attachment_fields", "attachment_buttons",
    ):
        if key in arguments:
            # RawWorkatoRuntime only expands ``____source`` for attachment
            # fields. A source-mapped button object is ignored by the live
            # request projection, so the executable WorkflowPlan must not
            # invent actions that were never sent.
            if (
                executable
                and key == "attachment_buttons"
                and isinstance(arguments[key], dict)
                and "____source" in arguments[key]
            ):
                continue
            payload[key] = deepcopy(arguments[key])
    return payload


def _has_meaningful_slack_attachment(arguments: dict[str, Any]) -> bool:
    """Whether the configured legacy attachment can produce any payload.

    Workato commonly serializes one blank editor row as ``[{}]``. The live
    connector drops that row, so field presence alone is not evidence for an
    ``attachments`` argument.
    """

    message = arguments.get("message")
    if isinstance(message, dict) and any(
        message.get(key) not in (None, "")
        for key in (
            "color", "pretext", "title", "title_link",
            "attachment_text", "footer", "footer_icon",
        )
    ):
        return True
    if any(
        arguments.get(key) not in (None, "")
        for key in (
            "color", "pretext", "title", "title_link",
            "attachment_text", "footer", "footer_icon",
        )
    ):
        return True
    for collection_key in ("attachment_fields", "attachment_buttons"):
        collection = arguments.get(collection_key)
        if isinstance(collection, dict):
            collection = [collection]
        if any(
            isinstance(item, dict)
            and any(value not in (None, "") for value in item.values())
            for item in collection or []
        ):
            return True
    return False


def _slack_text_argument(
    arguments: dict[str, Any], *, executable: bool = False
) -> Any:
    if executable:
        # Compile each configured Slack field before joining it.  Joining the
        # raw authoring strings first can turn a line-oriented Workato formula
        # into the middle of a larger template, where it is no longer parsed
        # as a formula and silently loses condition/reference semantics.
        return {
            "____canonical_slack_text": _slack_text_payload(arguments)
        }
    lines = _slack_configured_lines(arguments)
    if lines is None:
        return arguments.get("text") or ""
    if not all(isinstance(item, str) for item in lines):
        return arguments.get("text") or ""
    return "\n".join(lines)


def canonical_tool_arguments(
    tool: str,
    arguments: dict[str, Any],
    configured_object: Any = None,
    *,
    redact_dynamic_values: bool = True,
    source_tool: str | None = None,
    input_schema: Any = None,
    source_node: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project one raw recipe action into its canonical benchmark arguments."""

    normalize = public_configured_argument if redact_dynamic_values else deepcopy
    raw_tool = source_tool or tool
    if tool == "workato_db_table.get_records":
        projected = {
            key: arguments[key]
            for key in (
                "table_id",
                "filters",
                "continuation_token",
            )
            if key in arguments
        }
        projected["filters"] = [
            canonical_datatable_filter(
                item,
                redact_dynamic_values=redact_dynamic_values,
            )
            for item in projected.get("filters") or []
            if (
                not isinstance(item, dict)
                or item.get("field_id") not in (None, "")
                or any(
                    value not in (None, "")
                    for key, value in item.items()
                    if key != "field_id"
                )
            )
        ]
        # Workato exports editor defaults (limit="100", direction="asc") even
        # when the user configured no ordering.  They are authoring noise, not
        # connector arguments.  Non-default limits and an explicitly selected
        # order key are meaningful and are retained recipe-independently.
        raw_order_field = arguments.get("order_by_field_id")
        raw_limit = arguments.get("limit")
        if raw_limit not in (None, "") and (
            raw_limit not in ("100", 100)
            or raw_order_field not in (None, "")
        ):
            if isinstance(raw_limit, str) and raw_limit.isdigit():
                projected["limit"] = int(raw_limit)
            else:
                projected["limit"] = raw_limit
        if raw_order_field not in (None, ""):
            projected["order_by_field_id"] = (
                raw_order_field.replace("-", "_")
                if isinstance(raw_order_field, str)
                else raw_order_field
            )
            projected["order_direction"] = arguments.get("order_direction") or "asc"
        elif arguments.get("order_direction") not in (None, "") and raw_limit not in (
            None, "", "100", 100
        ):
            projected["order_direction"] = arguments.get("order_direction")
        return normalize(projected)
    if tool in WORKATO_DB_WRITE_TOOLS:
        projected: dict[str, Any] = {
            "table_id": arguments.get("table_id"),
            "record": _parameter_data(arguments),
        }
        if tool == "workato_db_table.add_record":
            projected["record_id_field"] = arguments.get("record_id_field")
        elif tool == "workato_db_table.update_record":
            projected["record_id"] = arguments.get("record_id") or arguments.get("id")
            projected["record_id_field"] = arguments.get("record_id_field")
        else:
            projected["primary_field_id"] = _workato_db_primary_field_id(
                arguments, input_schema, source_node
            )
        record = projected["record"]
        if isinstance(record, dict):
            projected["record"] = {
                str(key).replace("-", "_"): value
                for key, value in record.items()
            }
        return normalize(projected)
    if tool == "workato_db_table.delete_record":
        return normalize(
            {
                "table_id": arguments.get("table_id"),
                "record_id": arguments.get("record_id") or arguments.get("id"),
            }
        )
    if tool == "workato_db_table.truncate_table":
        return normalize({"table_id": arguments.get("table_id")})

    if tool.startswith("lookup_table."):
        projected = {"lookup_table_id": arguments.get("lookup_table_id")}
        if tool in {
            "lookup_table.get_entry",
            "lookup_table.update_entry",
            "lookup_table.delete_entry",
        }:
            projected["id"] = arguments.get("id")
        if tool in {
            "lookup_table.get_entry",
            "lookup_table.search_entries",
            "lookup_table.add_entry",
            "lookup_table.update_entry",
        }:
            projected["parameters"] = _parameter_data(arguments)
        if tool in {"lookup_table.update_entry", "lookup_table.delete_entry"}:
            projected["ignore_not_found"] = arguments.get("ignore_not_found")
        if tool == "lookup_table.add_batch_of_entries":
            raw_entries = arguments.get("entries")
            if isinstance(raw_entries, list):
                projected["entries"] = [
                    (
                        deepcopy(item.get("parameters"))
                        if isinstance(item, dict)
                        and isinstance(item.get("parameters"), dict)
                        else deepcopy(item)
                    )
                    for item in raw_entries
                    if isinstance(item, dict)
                ]
            elif isinstance(raw_entries, dict) and "____source" in raw_entries:
                params = raw_entries.get("parameters")
                projected["entries"] = {
                    "____source": deepcopy(raw_entries.get("____source")),
                    **(
                        deepcopy(params)
                        if isinstance(params, dict)
                        else {
                            str(key): deepcopy(item)
                            for key, item in raw_entries.items()
                            if key != "____source"
                        }
                    ),
                }
            else:
                projected["entries"] = deepcopy(raw_entries)
        return normalize(projected)

    if tool == "salesforce.search_records":
        if raw_tool == "salesforce.search_sobjects_soql_bulk_csv_v2":
            return normalize(
                {
                    "sobject": _salesforce_sobject_from_query(
                        arguments.get("query")
                    ),
                    "query": "Id != null",
                    "filters": [],
                }
            )
        if raw_tool == "salesforce.get_custom_object":
            sobject = (
                arguments.get("sobject_name")
                or arguments.get("object_name")
                or arguments.get("object")
                or configured_object
            )
            return normalize(
                {
                    "sobject": sobject,
                    "query": "",
                    "filters": [{"field": "Id", "value": arguments.get("id")}],
                    "limit": 1,
                }
            )
        raw_query = arguments.get("query")
        sobject = (
            _salesforce_sobject_from_query(raw_query)
            or arguments.get("sobject")
            or arguments.get("sobject_name")
            or configured_object
        )
        if not sobject and raw_query not in (None, ""):
            sobject = {"____canonical_salesforce_sobject": raw_query}
        projected: dict[str, Any] = {
            "sobject": sobject,
            "query": arguments.get("query") or "",
        }
        if arguments.get("limit") not in (None, ""):
            projected["limit"] = _canonical_optional_int(arguments["limit"])
        metadata_keys = {
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
        filters = []
        for key, value in arguments.items():
            if key in metadata_keys:
                continue
            filters.append({"field": "Id" if key == "id" else key, "value": value})
        if filters:
            projected["filters"] = filters
        return normalize(projected)
    if tool in {
        "salesforce.create_record",
        "salesforce.update_record",
        "salesforce.upsert_record",
    }:
        sobject = (
            arguments.get("sobject")
            or arguments.get("sobject_name")
            or configured_object
        )
        if tool == "salesforce.update_record" and raw_tool == "salesforce.composite_update_sobject":
            raw_records = arguments.get("records")

            def composite_record(record: dict[str, Any]) -> dict[str, Any]:
                fields = {
                    str(key): deepcopy(value)
                    for key, value in record.items()
                    if str(key)
                    not in {"Id", "id", "attributes", "____source"}
                }
                return {
                    "sobject": sobject,
                    "id": record.get("Id") or record.get("id"),
                    "fields": fields,
                }

            if isinstance(raw_records, dict) and "____source" in raw_records:
                projected_records: Any = {
                    "____source": deepcopy(raw_records.get("____source")),
                    **composite_record(raw_records),
                }
            elif isinstance(raw_records, list):
                projected_records = [
                    composite_record(record)
                    for record in raw_records
                    if isinstance(record, dict)
                ]
            else:
                projected_records = []
            return normalize(
                {"sobject": sobject, "records": projected_records}
            )
        source_fields: Any = arguments.get("records")
        if not isinstance(source_fields, dict):
            source_fields = arguments
        fields = {
            key: value
            for key, value in source_fields.items()
            if key
            not in {
                "____source",
                "advanced_configuration",
                "attributes",
                "batch_size",
                "id",
                "query_field",
                "sobject",
                "sobject_name",
            }
            and not (tool == "salesforce.update_record" and key == "Id")
        }
        projected = {"sobject": sobject, "fields": fields}
        if tool == "salesforce.update_record":
            projected["id"] = source_fields.get("Id") or arguments.get("id")
        elif tool == "salesforce.upsert_record":
            query_field = arguments.get("query_field") or {}
            projected["key_field"] = (
                query_field.get("primary_key")
                if isinstance(query_field, dict)
                else query_field
            )
        return normalize(projected)
    if tool in {
        "workato_recipe_function.return_result",
        "workato_genie.workflow_return_result",
    }:
        return normalize({"result": arguments.get("result") or {}})
    if tool == "workato_api_platform.return_response":
        projected = {
            "http_status_code": arguments.get("http_status_code") or "200",
            "response": _schema_convert(
                arguments.get("response") or {}, input_schema, "response"
            ),
        }
        if "response_headers" in arguments:
            projected["response_headers"] = _schema_convert(
                arguments.get("response_headers") or {},
                input_schema,
                "response_headers",
            )
        return normalize(projected)
    if tool == "workato_service.send_reply":
        projected = {
            "reply_type": arguments.get("reply_type") or "success",
            "reply": _schema_convert(
                arguments.get("reply") or {}, input_schema, "reply"
            ),
        }
        if "message" in arguments:
            projected["message"] = arguments.get("message")
        return normalize(projected)
    if tool in {"workato_service.call_service", "workato_service.call_service_async"}:
        # A synchronous call's runtime adapter additionally injects the hidden
        # seeded reply.  projection_support marks it runtime-dependent.
        return normalize(
            {
                "flow_id": arguments.get("flow_id"),
                "request": arguments.get("request") or {},
            }
        )

    if tool in {
        "snowflake.search_rows",
        "snowflake.search_rows_sql",
        "snowflake.run_custom_sql",
        "snowflake.update_rows",
        "snowflake.upsert_rows_batch",
    }:
        if tool == "snowflake.search_rows":
            projected = {
                "table": arguments.get("table"),
                "where": arguments.get("where") or "",
                "parameters": _snowflake_parameters(arguments),
                "limit": _canonical_optional_int(arguments.get("limit")),
                "offset": _canonical_optional_int(arguments.get("offset")),
                "orderby": arguments.get("orderby"),
                "output_columns": arguments.get("output_columns"),
            }
        elif tool == "snowflake.search_rows_sql":
            sql = arguments.get("sql")
            orderby = arguments.get("orderby")
            if (
                isinstance(sql, str)
                and isinstance(orderby, str)
                and orderby.strip()
                and not _sql_has_top_level_order_by(sql)
            ):
                sql = f"{sql.rstrip().rstrip(';')} ORDER BY {orderby}"
            projected = {
                "sql": sql,
                "parameters": _snowflake_parameters(arguments),
                "limit": _canonical_optional_int(arguments.get("limit")),
                "offset": _canonical_optional_int(arguments.get("offset")),
            }
        elif tool == "snowflake.run_custom_sql":
            projected = {
                "sql": arguments.get("sql"),
                "parameters": _snowflake_parameters(arguments),
            }
        elif tool == "snowflake.update_rows":
            projected = {
                "table": arguments.get("table"),
                "where": arguments.get("where"),
                "columns": arguments.get("columns") or {},
            }
        else:
            rows = arguments.get("rows") or []
            if isinstance(rows, dict) and "____source" not in rows:
                rows = [rows]
            projected = {
                "table": arguments.get("table"),
                "key_columns": arguments.get("key_columns")
                or _snowflake_primary_keys(input_schema),
                "rows": rows,
            }
        return normalize(projected)

    if tool == "workato_runtime.parse_json":
        return normalize({"document": arguments.get("document")})
    if tool == "workato_runtime.declare_variable":
        variables = arguments.get("variables")
        if isinstance(variables, dict):
            return normalize({"variables": variables})
        return normalize(
            {"name": arguments.get("name"), "value": arguments.get("value")}
        )
    if tool in {
        "workato_runtime.declare_list",
        "workato_runtime.update_variables",
        "workato_runtime.update_variable",
        "workato_runtime.insert_to_list",
        "workato_runtime.insert_to_list_batch",
    }:
        return normalize(arguments)
    if tool == "workato_runtime.accumulate_list_items":
        list_item = arguments.get("list_item")
        data = list_item.get("data") if isinstance(list_item, dict) else {}
        return normalize({"list_item": data if isinstance(data, dict) else {}})
    if tool == "workato_runtime.log_message":
        message: Any = arguments.get("message")
        if not redact_dynamic_values:
            # The raw logger adapter is a text boundary: Workato applies Ruby
            # ``to_s`` even when a bare datapill resolves to an object/list.
            # Keep that coercion explicit in WorkflowPlan instead of exposing
            # an object input_ref against the connector's string contract.
            message = {"____canonical_workato_text": message}
        return normalize(
            {
                "message": message,
                "log_level": str(arguments.get("log_level") or "INFO").upper(),
                "user_logs_enabled": _truthy_literal(
                    arguments.get("user_logs_enabled", True)
                ),
            }
        )

    if tool == "workato_smart_list.create_list":
        return normalize({"list_name": arguments.get("list_name")})
    if tool == "workato_smart_list.create_list_from_csv":
        raw_schema = arguments.get("csv_schema_json")
        try:
            schema = json.loads(raw_schema) if isinstance(raw_schema, str) else raw_schema
        except json.JSONDecodeError:
            schema = []
        columns = [
            str(item.get("name"))
            for item in schema or []
            if isinstance(item, dict) and item.get("name")
        ]
        return normalize(
            {"list_name": arguments.get("list_name"), "columns": columns}
        )
    if tool == "workato_smart_list.query_list":
        return normalize({"sql": arguments.get("sql")})

    if tool == "google_drive.create_folder":
        return normalize(
            {
                "parent_id": arguments.get("folderId") or arguments.get("parent_id"),
                "name": arguments.get("name"),
            }
        )
    if tool == "clock.wait_for_interval":
        return normalize({"interval": arguments.get("interval")})
    if tool == "slack_bot.get_user_by_email":
        if arguments.get("email") not in (None, ""):
            return normalize({"email": arguments.get("email")})
        return normalize({"id": arguments.get("id")})
    if tool == "slack.post_reply":
        delete_original = _truthy_literal(arguments.get("delete_original")) is True
        text = _slack_text_argument(
            arguments, executable=not redact_dynamic_values
        )
        if (
            not redact_dynamic_values
            and delete_original
            and not _slack_text_payload(arguments)
        ):
            text = ""
        projected: dict[str, Any] = {
            "text": text,
            # Unlike post_message, the reply connector actually receives the
            # resolved Block Kit payload.  Keep it alongside the text fallback
            # so interactive controls and fields remain executable.
            "blocks": arguments.get("blocks") or [],
        }
        for public_key, source_key in (
            ("ephemeral", "ephemeral_message"),
            ("replace_original", "replace_original"),
            ("delete_original", "delete_original"),
        ):
            configured = _truthy_literal(arguments.get(source_key))
            if configured is True:
                projected[public_key] = True
        return normalize(projected)
    if tool == "slack.post_message":
        advanced = arguments.get("advanced")
        advanced = advanced if isinstance(advanced, dict) else {}
        projected = {
            "channel": arguments.get("channel"),
            "text": _slack_text_argument(
                arguments, executable=not redact_dynamic_values
            ),
            "thread_ts": advanced.get("thread_ts") or "",
            "ts": advanced.get("ts") or "",
        }
        # Preserve the configured Block Kit structure in model-visible
        # occurrence documentation so the flattened canonical ``text`` value
        # is derivable. RawRecipeExecutor records that flattened text rather
        # than the Workato editor's block objects, so executable plan
        # projection deliberately omits this documentation-only field.
        if redact_dynamic_values and arguments.get("blocks"):
            projected["blocks"] = deepcopy(arguments["blocks"])
        # Legacy attachment projection is runtime-structured and remains a
        # declared non-exact class in the coverage report.  Preserve its raw
        # public fields rather than silently dropping them.
        if _has_meaningful_slack_attachment(arguments):
            projected["attachments"] = (
                arguments.get("attachments") or []
                if redact_dynamic_values
                else {
                    "____canonical_slack_attachments": (
                        _slack_attachment_payload(
                            arguments,
                            executable=True,
                        )
                    )
                }
            )
        return normalize(projected)
    if tool == "slack_bot.open_bot_app_home":
        blocks = deepcopy(arguments.get("blocks") or [])
        return normalize(
            {
                "user_id": arguments.get("user_id"),
                "view": {"blocks": blocks},
            }
        )
    if tool == "slack.update_blocks_by_block_id":
        return normalize(
            {
                "message_json": arguments.get("message_json"),
                "blocks_to_update": arguments.get("blocks_to_update") or [],
            }
        )
    if tool == "slack_bot.generate_menu_options":
        groups = arguments.get("option_groups")
        if groups and groups != [{}]:
            if (
                isinstance(groups, list)
                and len(groups) == 1
                and isinstance(groups[0], dict)
                and isinstance(groups[0].get("options"), list)
                and len(groups[0]["options"]) == 1
                and isinstance(groups[0]["options"][0], dict)
            ):
                mapped = {
                    "____source": groups[0].get("label"),
                    **deepcopy(groups[0]["options"][0]),
                }
                return normalize(
                    {
                        "options": mapped,
                        "option_groups": [{"options": deepcopy(mapped)}],
                    }
                )
            return normalize(
                {"options": arguments.get("options") or [], "option_groups": groups}
            )
        return normalize({"options": arguments.get("options") or []})
    if tool == "jira.create_issue":
        return normalize(
            {
                key: arguments.get(key)
                for key in (
                    "project_issuetype",
                    "summary",
                    "description",
                    "priority",
                    "labels",
                )
            }
        )
    if tool == "workato_pub_sub.publish_to_topic":
        return normalize(
            {
                "topic_id": arguments.get("topic_id"),
                "message": arguments.get("message") or {},
            }
        )
    if tool == "workato_pub_sub.publish_to_topic_batch":
        return normalize(
            {
                "topic_id": arguments.get("topic_id"),
                "messages": arguments.get("messages") or arguments.get("message") or [],
            }
        )

    if tool in {
        "workato_app.start_recipe",
        "workato_app.stop_recipe",
        "workato_app.get_recipe",
    }:
        return normalize(
            {
                "recipe_id": arguments.get("recipe_id")
                or arguments.get("recipe")
                or arguments.get("id")
            }
        )
    if tool == "workato_app.list_jobs":
        return normalize(
            {
                key: arguments[key]
                for key in ("recipe_id", "status")
                if arguments.get(key) not in (None, "")
            }
        )
    if tool == "workato_app.rerun_jobs":
        raw_jobs = arguments.get(
            "job_ids", arguments.get("jobs", arguments.get("job_id"))
        )
        jobs = raw_jobs if isinstance(raw_jobs, list) else [raw_jobs]
        job_ids: list[Any] = []
        projected: dict[str, Any] = {}
        if arguments.get("recipe_id") not in (None, ""):
            projected["recipe_id"] = arguments.get("recipe_id")
        for job in jobs:
            if isinstance(job, dict):
                job_ids.append(job.get("job_id") or job.get("id"))
                if job.get("recipe_id") not in (None, ""):
                    projected.setdefault("recipe_id", job.get("recipe_id"))
            else:
                job_ids.append(job)
        projected["job_ids"] = job_ids
        return normalize(projected)
    if tool == "workato_runtime.create_list":
        raw_size = arguments.get("size")
        if isinstance(raw_size, str) and raw_size.isdigit():
            raw_size = int(raw_size)
        return normalize(
            {"name": arguments.get("name") or "list", "size": raw_size}
        )

    if tool.startswith("google_sheets."):
        labels = _field_labels(input_schema, "data") or _field_labels(
            input_schema, "columns"
        ) or _field_labels(input_schema, "rows")
        spreadsheet = arguments.get("spreadsheet_id") or arguments.get("spreadsheet")
        sheet = arguments.get("sheet_name") or arguments.get("sheet")
        if tool == "google_sheets.add_spreadsheet_row_v4":
            if raw_tool == "google_sheets.add_row_v4_bulk":
                return normalize(
                    {
                        "spreadsheet": spreadsheet,
                        "sheet": sheet,
                        "headers": list(labels.values()),
                        "rows": _sheet_data(arguments.get("rows") or [], labels),
                    }
                )
            headers = arguments.get("column_headers")
            if isinstance(headers, str):
                headers = [line.strip() for line in headers.splitlines() if line.strip()]
            data = _sheet_data(
                arguments.get("columns") or arguments.get("data") or {},
                labels,
            )
            return normalize(
                {
                    "spreadsheet": spreadsheet,
                    "sheet": sheet,
                    # The raw adapter derives headers from the configured
                    # column keys actually present on this action, not every
                    # field advertised by the extended connector schema.
                    "headers": headers or list(data),
                    "data": data,
                }
            )
        if tool == "google_sheets.get_spreadsheet_rows_v4":
            return normalize(
                {"spreadsheet": spreadsheet, "sheet": sheet, "range": arguments.get("range")}
            )
        if tool == "google_sheets.search_spreadsheet_rows_v4_new":
            return normalize(
                {
                    "spreadsheet": spreadsheet,
                    "sheet": sheet,
                    "data": arguments.get("data") or {},
                    "count": _canonical_optional_int(arguments.get("count")),
                }
            )
        if tool == "google_sheets.update_row_v4_new":
            return normalize(
                {
                    "spreadsheet": spreadsheet,
                    "sheet": sheet,
                    "row_number": arguments.get("row_number"),
                    "data": _sheet_data(arguments.get("data") or {}, labels),
                }
            )
    return normalize(arguments)


# Compatibility aliases for existing callers.  New code should use the public
# names above so the adapter's role is explicit.
_public_configured_argument = public_configured_argument
_input_field_key_map = input_field_key_map
_canonical_datatable_filter = canonical_datatable_filter
_tool_configured_arguments = canonical_tool_arguments
