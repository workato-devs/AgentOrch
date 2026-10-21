from __future__ import annotations

import json
import re
from typing import Any

from .pipeline_common import stable_json_hash
from .recipe_semantics import reference_label, references


LEDGER_CATEGORIES = (
    "public_inputs",
    "domain_entities",
    "configured_filters",
    "fallback_rules",
    "data_transformations",
    "required_outputs",
    "validation_errors",
    "exception_rules",
    "terminal_rules",
)
LEDGER_EXTRACTOR_VERSION = "workflow-a-task-visible-ledger-v12"
UUID_SCHEMA_LABEL_RESOLUTION_VERSION = "uuid-schema-label-v1"
REPEAT_MARKER_ABSTRACTION_VERSION = "repeat-marker-abstraction-v1"
CUSTOM_SQL_ALTER_EFFECT_VERSION = "custom-sql-alter-effect-v1"
CUSTOM_SQL_EXTENDED_EFFECT_VERSION = "custom-sql-extended-effect-v1"
SLACK_QUALIFIED_LIFECYCLE_LABEL_VERSION = (
    "slack-qualified-lifecycle-label-v1"
)
_SEARCH_METADATA = {
    "field_list",
    "include_combined_attachments",
    "limit",
    "offset",
    "sobject_name",
    "table_list",
}

_IMPLEMENTATION_ARGUMENT_KEYS = {
    "advanced_configuration",
    "batch_size",
    "field_list",
    "input_schema",
    "ignore_not_found",
    "include_deleted_records",
    "include_combined_attachments",
    "include_header",
    "limit",
    "list_item_schema_json",
    "location",
    "name",
    "offset",
    "order_by_field_id",
    "order_direction",
    "output_columns",
    "output_schema",
    "page_size",
    "primary_field_id",
    "primary_index",
    "query_field",
    "query",
    "return_object",
    "retry",
    "schema",
    "search_all",
    "search_by",
    "sort_direction",
    "sql",
    "skip_delete_failed_job",
    "table_list",
    "update_only",
    "use_option_groups",
}
_OBJECT_ARGUMENT_KEYS = {
    "child_sobject_name",
    "lookup_table_id",
    "object",
    "object_name",
    "sheet",
    "sobject",
    "sobject_name",
    "spreadsheet",
    "table",
    "table_id",
}
_OPAQUE_FIELD_RE = re.compile(
    r"^(?:\$internal_value_)?[0-9a-f]{8}(?:[-_][0-9a-f]{4}){3}"
    r"[-_][0-9a-f]{12}$",
    flags=re.I,
)

_IMPLEMENTATION_ONLY_TRANSFORM_ACTION_MARKERS = (
    "accumulate_list_items",
    "parse_json",
    "workato_list.",
    "workato_smart_list.",
    "workato_variable.declare_list",
    "workato_variable.insert_to_list",
)


def control_flow_reachable_node_ids(
    workflow_a: dict[str, Any],
) -> set[str]:
    """Return nodes reachable from the trigger in A's executable CFG."""

    all_nodes = workflow_a.get("nodes") or []
    node_ids = {
        str(node.get("node_id") or "")
        for node in all_nodes
        if node.get("node_id")
    }
    reachable = {
        str(node.get("node_id") or "")
        for node in all_nodes
        if node.get("source_keyword") == "trigger"
    }
    if not reachable and all_nodes:
        reachable.add(str(all_nodes[0].get("node_id") or ""))
    control_flow_edges = workflow_a.get("control_flow_edges") or []
    if not control_flow_edges:
        return node_ids
    adjacency: dict[str, list[str]] = {
        node_id: [] for node_id in node_ids
    }
    for edge in control_flow_edges:
        source_id = str(edge.get("from") or "")
        target_id = str(edge.get("to") or "")
        if source_id in node_ids and target_id in node_ids:
            adjacency[source_id].append(target_id)
    pending = list(reachable)
    while pending:
        source_id = pending.pop()
        for target_id in adjacency.get(source_id) or []:
            if target_id in reachable:
                continue
            reachable.add(target_id)
            pending.append(target_id)
    return reachable


def task_effect_nodes(workflow_a: dict[str, Any]) -> list[dict[str, Any]]:
    """Return nodes whose configured behavior can affect an execution.

    Disabled nodes never execute. An unreachable action or terminal node also
    cannot contribute a user-visible requirement. Unreachable structural loop
    markers remain available because the canonical graph represents some loop
    conditions on their owning foreach node rather than linking the marker.
    """

    reachable = control_flow_reachable_node_ids(workflow_a)
    return [
        node
        for node in workflow_a.get("nodes") or []
        if node.get("skip") is not True
        and (
            str(node.get("node_id") or "") in reachable
            or (
                node.get("source_keyword") != "action"
                and (node.get("terminal") or {}).get("is_terminal") is not True
            )
        )
    ]


def _words(name: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    return [
        value.lower()
        for value in re.findall(r"[A-Za-z0-9]+", spaced.replace("_", " "))
        if value
    ]


def _human(name: str) -> str:
    return " ".join(_words(name))


def _display_path(parts: list[str]) -> str:
    value = ""
    for part in parts:
        if part == "[]":
            value += "[]"
        elif value:
            value += f".{part}"
        else:
            value = part
    return value


def public_input_facts(trigger: dict[str, Any]) -> list[dict[str, Any]]:
    """Return exact public paths, including fields nested in array items."""

    result: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()

    def add(
        path: list[str],
        field: dict[str, Any],
        required: bool,
        source: str,
    ) -> None:
        key = tuple(path)
        if not path or key in seen:
            return
        seen.add(key)
        result.append(
            {
                "name": str(path[-1]),
                "path": path,
                "type": str(field.get("type") or "unknown"),
                "label": str(
                    field.get("title")
                    or field.get("label")
                    or _human(path[-1])
                ),
                "required": required,
                "source": source,
            }
        )

    def visit(schema: Any, prefix: list[str]) -> None:
        if not isinstance(schema, dict):
            return
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            return
        required_names = {
            str(value) for value in schema.get("required") or []
        }
        for raw_name, raw_field in properties.items():
            name = str(raw_name)
            field = raw_field if isinstance(raw_field, dict) else {}
            path = [*prefix, name]
            field_type = str(field.get("type") or "unknown")
            required = name in required_names
            if field_type == "array":
                add(path, field, required, "public_input_schema")
                items = field.get("items")
                if isinstance(items, dict):
                    visit(items, [*path, "[]"])
            elif isinstance(field.get("properties"), dict):
                visit(field, path)
            else:
                add(path, field, required, "public_input_schema")

    visit(trigger.get("public_input_schema") or {}, [])
    for raw_field in trigger.get("public_inputs") or []:
        if not isinstance(raw_field, dict):
            continue
        name = str(raw_field.get("name") or "")
        path = [
            str(part)
            for part in (raw_field.get("path") or [name])
            if str(part)
        ]
        add(
            path,
            raw_field,
            bool(raw_field.get("required")),
            "public_inputs",
        )
    return result


def _path_names(text: str) -> list[str]:
    names = re.findall(
        r'(?:\\"|")path(?:\\"|")\s*:\s*\[(.*?)]',
        text,
        flags=re.S,
    )
    values: list[str] = []
    for payload in names:
        strings = re.findall(r'(?:\\"|")([^"\\]+)(?:\\"|")', payload)
        if strings:
            values.append(_human(strings[-1]))
    if not values:
        for match in re.findall(r"data\.[A-Za-z0-9_.]+", text):
            leaf = match.split(".")[-1]
            if leaf not in {"first", "rows"}:
                values.append(_human(leaf))
    return list(dict.fromkeys(values))


def _add(
    ledger: dict[str, list[dict[str, Any]]],
    category: str,
    *,
    description: str,
    evidence: list[str],
    anchors: list[list[str]],
    visibility: str = "user_visible",
    required_in_q: bool = True,
) -> None:
    item = {
        "ledger_id": f"{category}.{len(ledger[category]) + 1}",
        "description": description,
        "evidence": evidence,
        "visibility": visibility,
        "required_in_q": required_in_q,
        "lexical_anchors": anchors,
    }
    item["source_fact_hash"] = stable_json_hash(
        {
            "description": description,
            "evidence": evidence,
            "anchors": anchors,
        }
    )
    ledger[category].append(item)


def _condition_description(
    condition: dict[str, Any] | str,
    nodes_by_as: dict[str, dict[str, Any]] | None = None,
) -> tuple[str, list[list[str]]]:
    if isinstance(condition, str):
        text = condition.strip()
        if not text:
            return "the recorded control-flow condition", []
        lowered = text.lower()
        anchors: list[list[str]] = []
        if "has not raised an exception" in lowered:
            anchors.append(
                [
                    "processing succeeds",
                    "no exception",
                    "without an error",
                ]
            )
        elif "exception" in lowered or "error" in lowered:
            anchors.append(
                [
                    "exception",
                    "processing fails",
                    "error occurs",
                ]
            )
        return text, anchors
    clauses: list[str] = []
    anchors: list[list[str]] = []
    for part in condition.get("conditions") or []:
        if not isinstance(part, dict):
            continue
        lhs_names = (
            _formula_labels(part.get("lhs"), nodes_by_as or {})
            or _path_names(str(part.get("lhs") or ""))
        )
        lhs_names = [
            (
                "the event's repeat marker"
                if name.casefold() == "repeated job"
                else name
            )
            for name in lhs_names
        ]
        lhs_value = str(part.get("lhs") or "")
        without_references = re.sub(
            r"#?\{?_dp\('.*?'\)\}?",
            "",
            lhs_value,
        ).strip()
        if len(lhs_names) > 1 and not without_references:
            lhs = " immediately followed by ".join(lhs_names)
        else:
            lhs = lhs_names[-1] if lhs_names else "value"
        raw_operand = str(part.get("operand") or "")
        operand = {
            "blank": "blank",
            "present": "present",
            "equals": "equal to",
            "equals_to": "equal to",
            "equal_to": "equal to",
            "not_equal_to": "not equal to",
            "greater_than": "greater than",
            "less_than": "less than",
            "greater_than_or_equal_to": "at least",
            "less_than_or_equal_to": "at most",
            "is_true": "true",
            "is_not_true": "not true",
            "is_false": "false",
            "is_not_false": "not false",
            "starts_with": "starting with",
        }.get(raw_operand, raw_operand.replace("_", " "))
        rhs = part.get("rhs")
        clause = f"{lhs} is {operand}"
        if rhs not in (None, ""):
            rhs_names = _formula_labels(rhs, nodes_by_as or {})
            if isinstance(rhs, str) and re.fullmatch(
                r"-?[0-9]+(?:\.[0-9]+)?",
                rhs.strip(),
            ):
                rhs_description = rhs.strip()
            elif isinstance(rhs, str) and rhs.strip().lower() in {
                "true",
                "false",
                "null",
            }:
                rhs_description = rhs.strip().lower()
            else:
                rhs_description = _semantic_scalar(rhs, "unknown")
            clause += (
                f" {', then '.join(rhs_names)}"
                if rhs_names
                else f" {rhs_description}"
            )
        clauses.append(clause)
        if lhs != "size":
            anchors.append([lhs])
        if operand in {"blank", "present"}:
            anchors.append(
                ["absent", "missing", "not provided", "blank", "no identifier"]
                + (
                    [
                        "none supplied",
                        "none provided",
                        "none of the three",
                        "all three absent",
                        "all three empty",
                    ]
                    if operand == "blank"
                    else []
                )
                if operand == "blank"
                else ["provided", "present", "supplied"]
            )
        elif operand == "greater than" and str(rhs) == "0":
            anchors.append(
                ["exist", "results", "non-empty", "at least one", "one or more"]
            )
    joiner = " and " if condition.get("operand") == "and" else " or "
    return joiner.join(clauses) or json.dumps(condition, sort_keys=True), anchors


def _reply_fields(arguments: dict[str, Any]) -> dict[str, Any]:
    for key in ("reply", "data", "response"):
        if isinstance(arguments.get(key), dict):
            return arguments[key]
    return {}


def _custom_sql_effect(
    node: dict[str, Any],
) -> tuple[str, str, str] | None:
    """Return the active SQL verb, business operation, and target table.

    Generic custom-SQL connectors expose UI action names and table pick-list
    metadata that do not determine what the configured statement executes.
    The leading SQL statement is authoritative for the observable effect.
    """

    action = str(node.get("recipe_action") or "").lower()
    if "custom_sql" not in action:
        return None
    sql = str((node.get("configured_arguments") or {}).get("sql") or "")
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"--[^\n]*(?:\n|$)", " ", sql)
    sql = re.sub(r"^\s*=\s*['\"]", "", sql, count=1)
    create_match = re.search(
        r"^\s*CREATE\s+(?:(OR\s+REPLACE)\s+)?"
        r"(FILE\s+FORMAT|SCHEMA|TABLE|VIEW|STAGE|TASK)\s+"
        r"(?:IF\s+NOT\s+EXISTS\s+)?([^\s(;,]+)",
        sql,
        flags=re.I,
    )
    if create_match:
        replace = bool(create_match.group(1))
        object_kind = re.sub(
            r"\s+",
            " ",
            create_match.group(2).strip().lower(),
        )
        target = create_match.group(3).strip("'\"`[] ")
        if "#{_dp" in target:
            target = f"selected {object_kind}"
        statement = "create_" + object_kind.replace(" ", "_")
        operation = (
            "create or replace" if replace else "create"
        ) + f" a database {object_kind}"
        if object_kind == "file format" and re.search(
            r"\bCLONE\b", sql, flags=re.I
        ):
            operation += " by cloning the stated source"
        return statement, operation, target
    describe_match = re.search(
        r"^\s*(?:DESCRIBE|DESC)\s+(?:TABLE\s+)?([^\s(;,]+)",
        sql,
        flags=re.I,
    )
    if describe_match:
        target = describe_match.group(1).strip("'\"`[] ")
        if "#{_dp" in target:
            target = "selected table"
        return (
            "describe_table",
            "inspect a database table's columns",
            target,
        )
    alter_add_match = re.search(
        r"^\s*ALTER\s+TABLE\s+(.+?)\s+ADD(?:\s+COLUMN)?\b",
        sql,
        flags=re.I | re.S,
    )
    if alter_add_match:
        target = alter_add_match.group(1).strip("'\"`[] ")
        if "#{_dp" in target:
            target = "selected table"
        return (
            "alter_table_add",
            "alter a database table by adding the supplied definition",
            target,
        )
    extended_patterns = (
        (
            "alter_external_table_refresh",
            "refresh an external database table's metadata",
            r"^\s*ALTER\s+EXTERNAL\s+TABLE\s+(.+?)\s+REFRESH\b",
            "selected external table",
        ),
        (
            "alter_task_resume",
            "resume a scheduled database task",
            r"^\s*ALTER\s+TASK\s+(.+?)\s+RESUME\b",
            "selected database task",
        ),
        (
            "copy_into",
            "load staged data into a database table",
            r"^\s*COPY\s+INTO\s+(.+?)\s+FROM\b",
            "selected table",
        ),
        (
            "grant_select",
            "grant read access to a database object",
            r"^\s*GRANT\s+SELECT\s+ON\s+(.+?)\s+TO\s+ROLE\b",
            "selected database object",
        ),
        (
            "drop_table",
            "remove a database table",
            r"^\s*DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?([^\s;,]+)",
            "selected table",
        ),
    )
    for statement, operation, pattern, dynamic_target in extended_patterns:
        match = re.search(pattern, sql, flags=re.I | re.S)
        if match:
            target = match.group(1).strip("'\"`[] ")
            if "#{_dp" in target:
                target = dynamic_target
            return statement, operation, target
    patterns = (
        (
            "insert_overwrite",
            "replace table records",
            r"^\s*INSERT\s+OVERWRITE\s+INTO\s+([^\s(;,]+)",
        ),
        ("insert", "add a record", r"^\s*INSERT\s+INTO\s+([^\s(;,]+)"),
        ("update", "update records", r"^\s*UPDATE\s+([^\s(;,]+)"),
        ("delete", "delete records", r"^\s*DELETE\s+FROM\s+([^\s(;,]+)"),
        ("merge", "create or update records", r"^\s*MERGE\s+INTO\s+([^\s(;,]+)"),
        (
            "truncate",
            "empty a database table",
            r"^\s*TRUNCATE\s+(?:TABLE\s+)?([^\s(;,]+)",
        ),
        (
            "remove",
            "remove a staged file",
            r"^\s*REMOVE\s+['\"]?([^;]+?)['\"]?\s*;?\s*$",
        ),
        (
            "select",
            "retrieve matching records",
            r"^\s*SELECT\b.*?\bFROM\s+([^\s(;,]+)",
        ),
    )
    for statement, operation, pattern in patterns:
        match = re.search(pattern, sql, flags=re.I | re.S)
        if match:
            target = match.group(1).strip("'\"`[] ")
            if "#{_dp" in target:
                target = "configured staged file" if statement == "remove" else "selected table"
            return statement, operation, target
    return None


def _exception_scope_summary(
    node: dict[str, Any],
    nodes_by_as: dict[str, dict[str, Any]],
) -> tuple[str, list[str]]:
    """Describe one protected node without exposing orchestration identifiers."""

    action = str(node.get("recipe_action") or "")
    arguments = node.get("configured_arguments") or {}
    object_name = str(arguments.get("sobject_name") or "Salesforce records")
    if action.startswith("salesforce.search_sobjects"):
        return (
            f"searching {object_name}",
            ["search", _human(object_name)],
        )
    if any(
        marker in action
        for marker in ("search_object", "search_records")
    ):
        return (
            "retrieving matching business records",
            ["retrieve", "matching business records"],
        )
    custom_sql_effect = _custom_sql_effect(node)
    if custom_sql_effect is not None:
        statement, _, _ = custom_sql_effect
        descriptions = {
            "insert_overwrite": "replacing database-table records",
            "insert": "adding a database row",
            "update": "updating matching database rows",
            "delete": "deleting matching database rows",
            "merge": "creating or updating matching database rows",
            "truncate": "emptying a database table",
            "remove": "removing a staged file",
            "create_schema": "creating a database schema",
            "create_table": "creating a database table",
            "create_view": "creating or replacing a database view",
            "create_stage": "creating a database stage",
            "create_file_format": "creating a database file format",
            "create_task": "creating or replacing a scheduled database task",
            "describe_table": "inspecting a database table's columns",
            "alter_table_add": (
                "altering a database table by adding the supplied definition"
            ),
            "alter_external_table_refresh": (
                "refreshing an external database table's metadata"
            ),
            "alter_task_resume": "resuming a scheduled database task",
            "copy_into": "loading staged data into a database table",
            "grant_select": "granting read access to a database object",
            "drop_table": "removing a database table",
            "select": "retrieving matching database rows",
        }
        anchors = {
            "insert_overwrite": ["replace", "database-table records"],
            "insert": ["add", "database row"],
            "update": ["update", "matching database rows"],
            "delete": ["delete", "matching database rows"],
            "merge": ["create or update", "matching database rows"],
            "truncate": ["empty", "database table"],
            "remove": ["remove", "staged file"],
            "create_schema": ["create", "database schema"],
            "create_table": ["create", "database table"],
            "create_view": ["create or replace", "database view"],
            "create_stage": ["create", "database stage"],
            "create_file_format": ["create", "database file format"],
            "create_task": ["create or replace", "scheduled database task"],
            "describe_table": ["inspect", "database table columns"],
            "alter_table_add": [
                "alter",
                "database table",
                "supplied definition",
            ],
            "alter_external_table_refresh": [
                "refresh",
                "external database table metadata",
            ],
            "alter_task_resume": ["resume", "scheduled database task"],
            "copy_into": ["load", "staged data", "database table"],
            "grant_select": ["grant", "read access", "database object"],
            "drop_table": ["remove", "database table"],
            "select": ["retrieve", "matching database rows"],
        }
        return descriptions[statement], anchors[statement]
    if any(
        marker in action
        for marker in ("search_rows_sql", "search_rows")
    ):
        return (
            "retrieving matching database rows",
            ["retrieve", "matching database rows"],
        )
    if node.get("source_keyword") in {"if", "elsif"}:
        description, anchors = _condition_description(
            node.get("condition") or {},
            nodes_by_as,
        )
        return (
            f"evaluating whether {description}",
            [
                value
                for group in anchors
                for value in group
            ][:8],
        )
    if action == "workato_api_platform.return_response":
        status = str(arguments.get("http_status_code") or "")
        return (
            "returning the configured"
            + (f" HTTP {status}" if status else "")
            + " API response",
            ["return", "response", status],
        )
    if action == "workato_service.send_reply":
        reply_type = str(arguments.get("reply_type") or "")
        return (
            "returning the configured"
            + (f" {reply_type}" if reply_type else "")
            + " reply",
            ["return", "reply", reply_type],
        )
    if action == "workato_variable.declare_variable":
        variables = arguments.get("variables") or {}
        data = (
            variables.get("data")
            if isinstance(variables.get("data"), dict)
            else {}
        )
        fields = [_human(str(field)) for field in data]
        subject = " and ".join(fields) or "the required values"
        return f"computing {subject}", fields or ["computing values"]
    if action == "workato_smart_list.query_list":
        sql = str(arguments.get("sql") or "")
        upper_sql = sql.upper()
        table_match = re.search(
            r"\b(?:CREATE\s+TABLE|INSERT\s+INTO|FROM)\s+"
            r"([A-Za-z0-9_]+)",
            sql,
            flags=re.I,
        )
        subject = (
            _human(table_match.group(1))
            if table_match
            else "result"
        )
        if "CREATE TABLE" in upper_sql:
            return (
                f"initializing the {subject} result",
                ["initialize", subject],
            )
        if "INSERT INTO" in upper_sql:
            return (
                f"adding each item to the {subject} result",
                ["add each item", subject],
            )
        if "ORDER BY" in upper_sql:
            return (
                f"sorting the {subject} result",
                ["sort", subject],
            )
        return f"preparing the {subject} result", ["prepare", subject]
    if action == "workato_variable.update_variables":
        return "setting the computed values", ["set", "computed values"]
    if "parse_json" in action:
        return (
            "preparing the structured message content",
            ["prepare", "structured message content"],
        )
    if "accumulate_list_items" in action:
        return (
            "preparing the working message data",
            ["prepare", "working message data"],
        )
    if action in {
        "lookup_table.get_entry",
        "lookup_table.get_entries",
        "lookup_table.search_entries",
    }:
        return "retrieving the matching lookup-table entries", [
            "retrieve",
            "lookup table",
        ]
    if action in {
        "lookup_table.add_entry",
        "lookup_table.add_batch_of_entries",
    }:
        return "adding the lookup-table entries", ["add", "lookup table"]
    if action == "lookup_table.update_entry":
        return "updating the lookup-table entry", ["update", "lookup table"]
    if "get_user_by_email" in action:
        return "finding the messaging user by email", [
            "find",
            "user",
            "email",
        ]
    if action == "workato_service.call_service":
        service_name = _display_dynamic_value(
            (node.get("dynamic_pick_list_selection") or {}).get("flow_id")
        )
        if service_name:
            return (
                f"using the {service_name} business service",
                ["use", service_name, "business service"],
            )
    if action in {"logger.log_message", "workato_runtime.log_message"}:
        message = str(arguments.get("message") or "")
        names = _path_names(message)
        subject = names[-1] if names else "value"
        if "gsub" in message:
            return (
                f"preparing each {subject} for the result",
                ["prepare", subject],
            )
        return "producing the required log message", ["log message"]
    if node.get("source_keyword") == "foreach":
        names = _path_names(str(arguments.get("source") or ""))
        subject = names[-1] if names else "item"
        return (
            f"processing each {subject}",
            ["each", subject],
        )
    benchmark_tool = str(node.get("benchmark_tool") or "")
    if benchmark_tool:
        effect = benchmark_tool.rsplit(".", 1)[-1].replace("_", " ")
        return effect, [effect]
    if action:
        effect = action.rsplit(".", 1)[-1].replace("_", " ")
        return effect, [effect]
    return (
        str(node.get("source_keyword") or "protected processing"),
        ["protected processing"],
    )


def _exception_catch_outcome(
    catch_nodes: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    for node in catch_nodes:
        action = str(node.get("recipe_action") or "")
        arguments = node.get("configured_arguments") or {}
        serialized = json.dumps(arguments, ensure_ascii=False)
        includes_caught_message = all(
            marker in serialized
            for marker in ("provider", "catch", "message")
        )
        if action == "workato_api_platform.return_response":
            status = str(arguments.get("http_status_code") or "")
            message = (
                " containing the caught exception message"
                if includes_caught_message
                else ""
            )
            return (
                "return the configured"
                + (f" HTTP {status}" if status else "")
                + f" error response{message}",
                ["return", "error response", status, "caught error message"],
            )
        if action == "workato_service.send_reply":
            message = (
                " with the caught exception message"
                if includes_caught_message
                else ""
            )
            return (
                f"return an error reply{message}",
                ["return", "error reply", "caught error message"],
            )
        if str(node.get("benchmark_tool") or "") in {
            "slack.post_message",
            "slack.post_reply",
        }:
            message = (
                " containing the caught exception message"
                if includes_caught_message
                else ""
            )
            return (
                f"post a Slack error message{message}",
                ["post", "Slack error message", "caught error message"],
            )
        if node.get("source_keyword") == "stop":
            reason = str(arguments.get("stop_reason") or "")
            reason_labels = _formula_labels(
                reason,
                {
                    str(candidate.get("source_as") or ""): candidate
                    for candidate in catch_nodes
                    if candidate.get("source_as")
                },
            )
            visible_reason = (
                ", then ".join(reason_labels)
                if reason_labels
                else reason
            )
            return (
                "end processing"
                + (
                    " as an error"
                    if str(arguments.get("stop_with_error") or "").lower()
                    == "true"
                    else ""
                )
                + (
                    f" with reason {visible_reason}"
                    if visible_reason
                    else ""
                )
                + " without emitting an API response",
                [
                    "end processing",
                    "error",
                    visible_reason,
                    "no API response",
                ],
            )
    return (
        "follow the configured caught-error path",
        ["caught error", "error path"],
    )


def _joined_scope(items: list[str]) -> str:
    if not items:
        return "the protected operations"
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} or {items[1]}"
    return ", ".join(items[:-1]) + f", or {items[-1]}"


def _or_inequality_semantic_notes(predicate: str) -> list[str]:
    """Translate a same-field OR inequality under SQL three-valued logic."""

    pattern = re.compile(
        r"\b(?P<field>[A-Za-z][A-Za-z0-9_.]*)\s*(?:<>|!=)\s*"
        r"['\"](?P<left>[^'\"]+)['\"]\s+OR\s+"
        r"(?P=field)\s*(?:<>|!=)\s*['\"](?P<right>[^'\"]+)['\"]",
        flags=re.I,
    )
    return [
        (
            f"{match.group('field')} must be non-null; every non-null value "
            f"qualifies, including {match.group('left')} and "
            f"{match.group('right')}."
        )
        for match in pattern.finditer(predicate)
    ]


def _configured_reference_label(
    reference: dict[str, Any],
    nodes_by_as: dict[str, dict[str, Any]],
) -> str:
    """Name a formula input using only source structure present in A."""

    label = reference_label(reference)
    provider = str(reference.get("provider") or "")
    line = str(reference.get("line") or "")
    source = nodes_by_as.get(line)
    if provider == "catch":
        return label
    if provider in {"workato_service", "workato_api_platform"}:
        return label.removeprefix("request ") or label
    if source is None:
        return label
    resolved = _reference_path_label(
        reference,
        source.get("output_schema") or [],
    )
    if resolved:
        label = resolved
    source_args = source.get("configured_arguments") or {}
    source_object = str(
        (source.get("dynamic_pick_list_selection") or {}).get("sobject_name")
        or (source.get("dynamic_pick_list_selection") or {}).get("table_id")
        or (source.get("dynamic_pick_list_selection") or {}).get(
            "lookup_table_id"
        )
        or source_args.get("sobject_name")
        or source_args.get("object_name")
        or source_args.get("table_id")
        or ""
    )
    if source_object:
        return f"{_human(source_object)} {label}".strip()
    return label


def _formula_labels(
    value: Any,
    nodes_by_as: dict[str, dict[str, Any]],
) -> list[str]:
    return list(
        dict.fromkeys(
            _configured_reference_label(item, nodes_by_as)
            for item in references(value)
        )
    )


def _formula_labels_without_execution_context(
    value: Any,
    nodes_by_as: dict[str, dict[str, Any]],
) -> list[str]:
    return list(
        dict.fromkeys(
            _configured_reference_label(item, nodes_by_as)
            for item in references(value)
            if str(item.get("pill_type") or "") != "job_context"
        )
    )


def canonical_query_field_name(value: Any) -> str:
    """Remove connector display labels from a relationship-field token."""

    field = str(value or "").strip()
    if not field or ("$" not in field and "--" not in field):
        return field
    relationship, separator, leaf = field.rpartition(".")
    if not separator:
        relationship = field
        leaf = ""
    path = [
        segment.split("$", 1)[0].strip()
        for segment in relationship.split("--")
        if segment.split("$", 1)[0].strip()
    ]
    if leaf:
        path.append(leaf)
    return ".".join(path)


def _selected_field_entries(args: dict[str, Any]) -> list[str]:
    value = args.get("field_list")
    if isinstance(value, list):
        fields = [str(item) for item in value]
    elif isinstance(value, str):
        fields = re.split(r"[\n,]+", value)
    else:
        fields = []
    return [
        canonical_query_field_name(item)
        for item in fields
        if item.strip()
    ]


def _schema_field_map(fields: Any) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for field in fields or []:
        if not isinstance(field, dict):
            continue
        name = str(field.get("name") or "")
        if name:
            result[name] = {
                "label": str(field.get("label") or _human(name)),
                "type": str(field.get("type") or "unknown"),
            }
        result.update(_schema_field_map(field.get("properties")))
    return result


def _normalized_field_identifier(value: Any) -> str:
    """Normalize Workato UUID column IDs across input/output spellings."""

    return re.sub(r"[^a-z0-9]", "_", str(value or "").lower())


def _schema_field_for_identifier(
    node: dict[str, Any],
    identifier: Any,
) -> dict[str, str]:
    """Resolve an opaque configured field ID through the action schemas.

    Some exported recipes carry stale ``dynamicPickListSelection`` indexes:
    the display labels for adjacent filters are swapped even though each
    filter's UUID and the action output schema still agree.  The UUID-backed
    schema is the executable contract, so it must win over the positional UI
    metadata when both are present.
    """

    normalized = _normalized_field_identifier(identifier)
    if not normalized:
        return {}
    for schema_key in ("output_schema", "input_schema"):
        fields = _schema_field_map(node.get(schema_key))
        for name, field in fields.items():
            if _normalized_field_identifier(name) != normalized:
                continue
            label = str(field.get("label") or "")
            if label and not label.startswith("$internal_value"):
                return field
    return {}


def _reference_path_label(
    reference: dict[str, Any],
    fields: Any,
) -> str:
    metadata = _schema_field_map(fields)
    labels: list[str] = []
    current_fields = [
        field for field in fields or [] if isinstance(field, dict)
    ]
    for part in reference.get("path") or []:
        if isinstance(part, dict):
            marker = str(part.get("path_element_type") or "")
            if marker == "size":
                labels.append("count")
            continue
        name = str(part)
        field = next(
            (
                candidate
                for candidate in current_fields
                if str(candidate.get("name") or "") == name
            ),
            None,
        )
        if field is not None:
            if name.lower() not in {"records", "rows", "result", "items"}:
                labels.append(str(field.get("label") or _human(name)))
            current_fields = [
                child
                for child in field.get("properties") or []
                if isinstance(child, dict)
            ]
        elif name.lower() in {"records", "rows", "result", "items"}:
            continue
        elif (item := metadata.get(name)) is not None:
            labels.append(item["label"])
            current_fields = []
        elif not _OPAQUE_FIELD_RE.fullmatch(name):
            labels.append(_human(name))
            current_fields = []
    return " ".join(dict.fromkeys(value for value in labels if value))


def _semantic_scalar(value: Any, field_type: str) -> str:
    # Configured JSON primitive types are execution semantics. Connector
    # schemas can describe a business column as boolean while the simulator
    # and gold tool call intentionally preserve the configured text "true".
    # Formula conversions are summarized separately by _formula_value_summary.
    del field_type
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _display_dynamic_value(value: Any) -> str:
    if isinstance(value, list):
        labels = [
            str(item.get("label") or item.get("value") or "")
            for item in value
            if isinstance(item, dict)
        ]
        return ", ".join(label for label in labels if label)
    if isinstance(value, dict):
        return str(value.get("label") or value.get("value") or "")
    return str(value or "")


def _formula_value_summary(
    value: Any,
    nodes_by_as: dict[str, dict[str, Any]],
) -> str:
    labels = _formula_labels(value, nodes_by_as)
    if not labels:
        return ""
    summary = ", then ".join(labels)
    if isinstance(value, str):
        lowered = value.lower()
        if ".to_i" in lowered:
            summary += " converted to an integer"
        elif ".to_f" in lowered:
            summary += " converted to a number"
        elif ".to_s" in lowered:
            summary += " converted to text"
        if "smart_join" in lowered:
            separator_match = re.search(
                r"smart_join\([\"'](?P<separator>.*?)[\"']\)",
                value,
                flags=re.S,
            )
            separator = (
                separator_match.group("separator")
                if separator_match
                else ""
            )
            summary += f" joined with {separator!r}"
    return summary


def _business_binding_source(source: str) -> str:
    """Remove connector traversal wrappers from a business-effect binding."""

    value = re.sub(
        r"\breply Message each item\s+",
        "stored message ",
        source,
        flags=re.I,
    )
    value = re.sub(
        r"\breply Message first\s+",
        "first stored message ",
        value,
        flags=re.I,
    )
    value = re.sub(
        r"\breply Message\s+",
        "stored message ",
        value,
        flags=re.I,
    )
    value = re.sub(
        r"\bDocument Array\s+",
        "parsed item ",
        value,
        flags=re.I,
    )
    replacements = {
        "context channel": "incoming Slack channel",
        "context user name": "invoking Slack user name",
        "job id": "processing identifier",
        "job url": "processing link",
        "recipe id": "automation identifier",
        "recipe name": "process name",
    }
    for raw, business in replacements.items():
        value = re.sub(rf"\b{re.escape(raw)}\b", business, value, flags=re.I)
    if value.strip().lower() == "ts":
        value = "triggering Slack message timestamp"
    return value


def _mapping_entries(
    value: Any,
    nodes_by_as: dict[str, dict[str, Any]],
    fields: dict[str, dict[str, str]],
    dynamic: dict[str, Any],
    path: tuple[str, ...] = (),
    exclude_execution_context: bool = False,
) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            if (
                key_text.startswith("____")
                or key_text == "attributes"
                or (not path and key_text == "filters")
                or (
                    not path
                    and key_text in _IMPLEMENTATION_ARGUMENT_KEYS
                )
                or (not path and key_text in _OBJECT_ARGUMENT_KEYS)
                or _OPAQUE_FIELD_RE.fullmatch(key_text)
                and not fields.get(key_text)
            ):
                continue
            entries.extend(
                _mapping_entries(
                    item,
                    nodes_by_as,
                    fields,
                    dynamic,
                    path + (key_text,),
                    exclude_execution_context,
                )
            )
        return entries
    if isinstance(value, list):
        for index, item in enumerate(value):
            entries.extend(
                _mapping_entries(
                    item,
                    nodes_by_as,
                    fields,
                    dynamic,
                    path + (str(index),),
                    exclude_execution_context,
                )
            )
        return entries
    if not path:
        return entries
    key = path[-1]
    full_path = ".".join(path)
    field = fields.get(key) or {}
    dynamic_label = _display_dynamic_value(dynamic.get(full_path))
    target = str(
        dynamic_label
        or field.get("label")
        or _human(key)
    )
    if key.lower() == "dm" and any(
        segment.lower() == "channel_name" for segment in path[:-1]
    ):
        target = "Channel"
    if (
        not dynamic_label
        and (
            target.startswith("$internal_value")
            or _OPAQUE_FIELD_RE.fullmatch(target)
        )
    ):
        return entries
    visible_labels = (
        _formula_labels_without_execution_context(value, nodes_by_as)
        if exclude_execution_context
        else []
    )
    formula_summary = (
        ", then ".join(visible_labels)
        if exclude_execution_context and visible_labels
        else (
            ""
            if exclude_execution_context
            else _formula_value_summary(value, nodes_by_as)
        )
    )
    source = (
        formula_summary
        if formula_summary
        else _semantic_scalar(value, str(field.get("type") or "unknown"))
    )
    entries.append((target, source))
    return entries


def _active_filter_keys(
    arguments: dict[str, Any], raw_filter: dict[str, Any]
) -> tuple[Any, Any]:
    """Select the operator/value option group matching the field type."""

    field_key = next(
        (
            key
            for key in raw_filter
            if str(key) in {"field", "field_id", "column"}
            or str(key).startswith("field_")
        ),
        None,
    )
    field_value = raw_filter.get(field_key) if field_key is not None else ""
    field_type = str(arguments.get(field_value) or "").lower()
    type_suffix = {
        "string": "default",
        "text": "default",
        "integer": "integer",
        "number": "integer",
        "id": "id",
        "relation": "relation",
        "boolean": "boolean",
        "date": "date",
        "date_time": "date_time",
        "datetime": "date_time",
    }.get(field_type, field_type)
    operator_keys = [
        key for key in raw_filter if str(key).startswith("op_")
    ]
    preferred_operator_key = f"op_{type_suffix}"
    operator_key = (
        preferred_operator_key
        if preferred_operator_key in raw_filter
        else next(iter(operator_keys), None)
    )
    value_keys = [
        key
        for key in raw_filter
        if str(key).startswith("value_") or str(key) == "value"
    ]
    preferred_value_key = f"value_{type_suffix}"
    if type_suffix == "id" and preferred_value_key not in raw_filter:
        preferred_value_key = "value_default"
    value_key = (
        preferred_value_key
        if preferred_value_key in raw_filter
        else next(iter(value_keys), None)
    )
    return operator_key, value_key


def _configured_action_filters(
    node: dict[str, Any],
    nodes_by_as: dict[str, dict[str, Any]],
) -> list[tuple[str, list[list[str]]]]:
    arguments = node.get("configured_arguments") or {}
    dynamic = node.get("dynamic_pick_list_selection") or {}
    operator_names = {
        "eq": "equals",
        "equals": "equals",
        "isfalse": "is boolean false",
        "istrue": "is boolean true",
        "neq": "does not equal",
        "not_equal": "does not equal",
        "contains": "contains",
        "starts_with": "starts with",
    }
    effects: list[tuple[str, list[list[str]]]] = []
    for container_name in ("filters",):
        configured = arguments.get(container_name)
        if not isinstance(configured, list):
            continue
        for index, raw_filter in enumerate(configured):
            if not isinstance(raw_filter, dict) or not raw_filter:
                continue
            field_key = next(
                (
                    key
                    for key in raw_filter
                    if str(key) in {"field", "field_id", "column"}
                    or str(key).startswith("field_")
                ),
                None,
            )
            if field_key is None:
                continue
            field_value = (
                raw_filter.get(field_key) if field_key is not None else ""
            )
            dynamic_path = (
                f"{container_name}.{index}.{field_key}"
                if field_key is not None
                else ""
            )
            schema_field = _schema_field_for_identifier(node, field_value)
            field = str(
                schema_field.get("label")
                or _display_dynamic_value(dynamic.get(dynamic_path))
                or field_value
                or "the selected field"
            )
            if _OPAQUE_FIELD_RE.fullmatch(field):
                field = "the selected field"
            operator_key, value_key = _active_filter_keys(
                arguments, raw_filter
            )
            operator_value = str(
                raw_filter.get(operator_key) if operator_key else "equals"
            ).lower()
            operator = operator_names.get(
                operator_value,
                _human(operator_value),
            )
            raw_value = (
                raw_filter.get(value_key) if value_key is not None else None
            )
            value_summary = _formula_value_summary(
                raw_value,
                nodes_by_as,
            )
            if not value_summary and value_key is not None:
                field_type = str(value_key).removeprefix("value_")
                value_summary = _semantic_scalar(raw_value, field_type)
            if operator in {"is boolean false", "is boolean true"}:
                description = f"Filter {field} so it {operator}."
            elif value_key is not None:
                description = (
                    f"Filter {field} so it {operator} {value_summary}."
                )
            else:
                description = f"Filter {field} using {operator}."
            effects.append(
                (
                    description,
                    [
                        [field, _human(field)],
                        [operator],
                        *([[value_summary]] if value_summary else []),
                    ],
                )
            )
    return effects


def _schema_filter_label_overrides(
    workflow_a: dict[str, Any],
) -> list[dict[str, str]]:
    """Record cases where UUID schema labels supersede stale UI positions."""

    overrides: list[dict[str, str]] = []
    for node in workflow_a.get("nodes") or []:
        arguments = node.get("configured_arguments") or {}
        dynamic = node.get("dynamic_pick_list_selection") or {}
        configured = arguments.get("filters")
        if not isinstance(configured, list):
            continue
        for index, raw_filter in enumerate(configured):
            if not isinstance(raw_filter, dict):
                continue
            field_key = next(
                (
                    key
                    for key in raw_filter
                    if str(key) in {"field", "field_id", "column"}
                    or str(key).startswith("field_")
                ),
                None,
            )
            if field_key is None:
                continue
            field_value = raw_filter.get(field_key)
            schema_label = str(
                _schema_field_for_identifier(node, field_value).get("label")
                or ""
            )
            dynamic_path = f"filters.{index}.{field_key}"
            dynamic_label = _display_dynamic_value(dynamic.get(dynamic_path))
            if (
                schema_label
                and dynamic_label
                and schema_label.casefold() != dynamic_label.casefold()
            ):
                overrides.append(
                    {
                        "node_id": str(node.get("node_id") or ""),
                        "field_path": dynamic_path,
                        "field_id": str(field_value or ""),
                        "schema_label": schema_label,
                        "ignored_dynamic_label": dynamic_label,
                    }
                )
    return overrides


def _configured_query_filter(
    predicate: str,
    nodes_by_as: dict[str, dict[str, Any]],
) -> tuple[str, list[list[str]]]:
    """Summarize a SQL/SOQL predicate without exposing query syntax."""

    where_match = re.search(
        r"\bWHERE\b(?P<where>.*?)(?:\bGROUP\s+BY\b|\bORDER\s+BY\b|$)",
        predicate,
        flags=re.I | re.S,
    )
    condition_text = (
        where_match.group("where") if where_match else predicate
    )
    fields = list(
        dict.fromkeys(
            match.group(1)
            for match in re.finditer(
                r"\b([A-Za-z][A-Za-z0-9_.]*(?:__c|__r)?)\s*"
                r"(?:=|<>|!=|<=|>=|<|>|\bLIKE\b|\bIN\b)",
                condition_text,
                flags=re.I,
            )
            if not _OPAQUE_FIELD_RE.fullmatch(match.group(1))
        )
    )
    references_in_query = _formula_labels(predicate, nodes_by_as)
    literal_rules: list[str] = []
    operator_names = {
        "=": "equals",
        "!=": "does not equal",
        "<>": "does not equal",
        ">": "is greater than",
        "<": "is less than",
        ">=": "is at least",
        "<=": "is at most",
        "LIKE": "matches",
    }
    for match in re.finditer(
        r"\b([A-Za-z][A-Za-z0-9_.]*(?:__c|__r)?)\s*"
        r"(=|<>|!=|<=|>=|<|>|\bLIKE\b)\s*"
        r"'([^']*)'",
        condition_text,
        flags=re.I,
    ):
        field, operator, literal = match.groups()
        if "_dp(" in literal or "#{" in literal:
            continue
        literal_rules.append(
            f"{field} {operator_names.get(operator.upper(), operator)} "
            f"the string {literal!r}"
        )
    for match in re.finditer(
        r"\b([A-Za-z][A-Za-z0-9_.]*(?:__c|__r)?)\s+IN\s*"
        r"\((?P<values>(?:\s*'[^']*'\s*,?)+)\)",
        condition_text,
        flags=re.I,
    ):
        values = re.findall(r"'([^']*)'", match.group("values"))
        if values and not any("_dp(" in value or "#{" in value for value in values):
            literal_rules.append(
                f"{match.group(1)} is one of "
                + ", ".join(repr(value) for value in values)
            )
    parts = [
        (
            "Select records using the configured logical conditions on "
            + ", ".join(fields)
            + "."
            if fields
            else "Select records using the configured logical conditions."
        )
    ]
    if references_in_query:
        parts.append(
            "Use values from "
            + ", ".join(references_in_query)
            + " in those conditions."
        )
    if literal_rules:
        parts.append("Literal conditions: " + "; ".join(literal_rules) + ".")
    semantic_notes = _or_inequality_semantic_notes(predicate)
    if semantic_notes:
        parts.append("Effective boolean semantics: " + " ".join(semantic_notes))
    return (
        " ".join(parts),
        [
            *[[field, _human(field)] for field in fields],
            *[[value] for value in references_in_query],
            *[[value] for value in literal_rules],
        ],
    )


def _walk_leaf_values(
    value: Any,
    path: tuple[str, ...] = (),
) -> list[tuple[tuple[str, ...], Any]]:
    if isinstance(value, dict):
        return [
            pair
            for key, item in value.items()
            for pair in _walk_leaf_values(item, path + (str(key),))
        ]
    if isinstance(value, list):
        return [
            pair
            for index, item in enumerate(value)
            for pair in _walk_leaf_values(item, path + (str(index),))
        ]
    return [(path, value)]


def _formula_effects(
    node: dict[str, Any],
    nodes_by_as: dict[str, dict[str, Any]],
) -> list[tuple[str, list[list[str]]]]:
    """Translate known formula families and inventory unknown computations."""

    action = str(node.get("recipe_action") or "")
    if any(
        token in action
        for token in (
            "query_list",
            "declare_variable",
            "log_message",
            "search_sobjects",
            "custom_sql",
            "search_rows_sql",
            "__adhoc_http_action",
        )
    ):
        return []
    field_map = _schema_field_map(node.get("input_schema"))
    dynamic = node.get("dynamic_pick_list_selection") or {}
    effects: list[tuple[str, list[list[str]]]] = []
    for path, value in _walk_leaf_values(
        node.get("configured_arguments") or {}
    ):
        if not isinstance(value, str):
            continue
        stripped = value.strip()
        if not (
            stripped.startswith("=")
            or "_dp(" in value
            or "_('data." in value
        ):
            continue
        if " or " in value or "smart_join" in value:
            continue
        # Plain datapill interpolation is a binding, not a transformation.
        without_refs = re.sub(r"#?\{?_dp\('.*?'\)\}?", "", value)
        without_refs = re.sub(r"_\('data\..*?'\)", "", without_refs)
        if not re.search(r"[A-Za-z0-9]", without_refs.lstrip("= ")):
            continue
        if path and (
            path[0] in _IMPLEMENTATION_ARGUMENT_KEYS
            or path[0] in _OBJECT_ARGUMENT_KEYS
            or path[0] == "filters"
        ):
            continue
        raw_target = path[-1] if path else "configured value"
        if (
            str(node.get("benchmark_tool") or "")
            in {"slack.post_message", "slack.post_reply"}
            and str(raw_target).lower()
            in {"block_type", "bot_command", "params", "type"}
        ):
            continue
        field = field_map.get(raw_target) or {}
        target = str(
            _display_dynamic_value(dynamic.get(".".join(path)))
            or field.get("label")
            or _human(raw_target)
        )
        if (
            target.startswith("$internal_value")
            or _OPAQUE_FIELD_RE.fullmatch(target)
        ):
            continue
        labels = (
            _formula_labels_without_execution_context(value, nodes_by_as)
            if str(node.get("benchmark_tool") or "") == "email.send_mail"
            else _formula_labels(value, nodes_by_as)
        )
        if str(node.get("benchmark_tool") or "") in {
            "slack.post_message",
            "slack.post_reply",
        }:
            labels = [_business_binding_source(label) for label in labels]
        lowered = value.lower()
        if ".to_date...today" in lowered and ".count" in lowered:
            description = (
                f"Compute {target} as the count of calendar-day boundaries "
                f"from {', '.join(labels) if labels else 'the source date'} "
                "up to but excluding today."
            )
            anchors = [
                ["calendar day", "day boundaries", "days elapsed"],
                ["excluding today", "before today"],
                *[[label] for label in labels],
            ]
        elif (
            ".reverse" in lowered
            and "gsub" in lowered
            and ("\\d{3}" in value or "three" in lowered)
        ):
            description = (
                f"Format {target} with comma thousands separators"
                + (
                    f" using {', '.join(labels)}."
                    if labels
                    else "."
                )
            )
            anchors = [
                ["comma thousands separators", "thousands-separated"],
                *[[label] for label in labels],
            ]
        elif ".to_i" in lowered:
            description = (
                f"Convert {', '.join(labels) if labels else 'the source value'} "
                f"to an integer for {target}."
            )
            anchors = [
                ["integer", "whole number"],
                [target],
                *[[label] for label in labels],
            ]
        elif ".to_f" in lowered:
            description = (
                f"Convert {', '.join(labels) if labels else 'the source value'} "
                f"to a number for {target}."
            )
            anchors = [
                ["number", "numeric"],
                [target],
                *[[label] for label in labels],
            ]
        elif ".to_s" in lowered:
            description = (
                f"Convert {', '.join(labels) if labels else 'the source value'} "
                f"to text for {target}."
            )
            anchors = [
                ["text", "string"],
                [target],
                *[[label] for label in labels],
            ]
        else:
            description = (
                f"Compute {target} from "
                f"{', '.join(labels) if labels else 'its configured inputs'} "
                "using the configured business transformation."
            )
            anchors = [[target], *[[label] for label in labels]]
        if str(node.get("benchmark_tool") or "") in {
            "slack.post_message",
            "slack.post_reply",
        }:
            visible_labels = list(
                dict.fromkeys(
                    match.group(0)
                    for match in re.finditer(
                        r"\b(?:(?:Internal|External|Original)\s+)?"
                        r"(?:Recipe|Job) (?:ID|URL|name)\b",
                        value,
                        flags=re.I,
                    )
                )
            )
            if visible_labels:
                description += (
                    " Preserve these exact visible Slack labels: "
                    + ", ".join(
                        json.dumps(label, ensure_ascii=False)
                        for label in visible_labels
                    )
                    + "."
                )
                anchors.extend([[label] for label in visible_labels])
        effects.append((description, anchors))
    return effects


def _action_effect_description(
    node: dict[str, Any],
    nodes_by_as: dict[str, dict[str, Any]],
) -> tuple[str, list[list[str]], str] | None:
    """Build a connector-agnostic effect fact for externally relevant actions."""

    action = str(node.get("recipe_action") or "")
    benchmark_tool = str(node.get("benchmark_tool") or "")
    if not action or not benchmark_tool:
        return None
    if any(
        token in action
        for token in (
            "search_sobjects",
            "send_reply",
            "return_response",
            "return_result",
            "query_list",
            "declare_variable",
            "log_message",
        )
    ):
        return None
    args = node.get("configured_arguments") or {}
    dynamic = node.get("dynamic_pick_list_selection") or {}
    fields = _schema_field_map(node.get("input_schema"))
    action_name = action.rsplit(".", 1)[-1].lower()
    is_adhoc_http = "__adhoc_http_action" in action_name
    is_slack_message = benchmark_tool in {
        "slack.post_message",
        "slack.post_reply",
    }
    slack_lifecycle_labels = (
        list(
            dict.fromkeys(
                match.group(0)
                for match in re.finditer(
                    r"\b(?:(?:Internal|External|Original)\s+)?"
                    r"(?:Recipe|Job) (?:ID|URL|name)\b",
                    json.dumps(args, ensure_ascii=False),
                    flags=re.I,
                )
            )
        )
        if is_slack_message
        else []
    )
    is_callable_service = action == "workato_service.call_service"
    excludes_execution_context = benchmark_tool == "email.send_mail"
    mapping_args = args
    if is_callable_service and "flow_id" in args:
        mapping_args = {
            key: value for key, value in args.items() if key != "flow_id"
        }
    elif is_slack_message:
        # Slack block encodings and interaction callbacks are connector
        # plumbing.  Retain the visible destination/content/style mappings,
        # while describing update/thread behavior separately below.
        mapping_args = {
            key: value for key, value in args.items() if key != "advanced"
        }
    elif is_adhoc_http:
        # Ad-hoc connector actions carry editor metadata beside the actual
        # request body: mnemonic text, response schemas, header schemas, and
        # request/response UI modes.  Those values configure the connector
        # editor and are not business requirements for an implementation.
        # Retain only the request-body binding here; method and destination
        # are described explicitly below.
        configured_input = args.get("input")
        mapping_args = (
            configured_input if isinstance(configured_input, dict) else {}
        )
    mappings = _mapping_entries(
        mapping_args,
        nodes_by_as,
        fields,
        dynamic,
        exclude_execution_context=excludes_execution_context,
    )
    if excludes_execution_context:
        recipient_property = re.search(
            r'"property_name"\s*:\s*"([^\"]+)"',
            str(args.get("to") or ""),
        )
        if recipient_property:
            mappings = [
                (
                    field,
                    _human(recipient_property.group(1))
                    if field.lower() == "to"
                    else source,
                )
                for field, source in mappings
            ]
    if is_slack_message:
        mappings = [
            (field, _business_binding_source(source))
            for field, source in mappings
            if field.lower()
            not in {"block type", "bot command", "params", "type"}
        ]
    elif is_callable_service:
        mappings = [
            (field, _business_binding_source(source))
            for field, source in mappings
        ]
    elif is_adhoc_http:
        mappings = [
            (
                "request body" if field.lower() == "data" else field,
                _business_binding_source(source),
            )
            for field, source in mappings
        ]
    custom_sql_effect = _custom_sql_effect(node)
    if custom_sql_effect is not None:
        _, operation, _ = custom_sql_effect
    elif is_adhoc_http:
        operation = "send an HTTP request"
    elif "generate_menu_options" in action_name:
        operation = "produce selectable menu options"
    elif "get_user_by_email" in action_name:
        operation = "find the messaging user by email"
    elif any(
        marker in action_name
        for marker in ("get_", "search_", "run_custom_sql")
    ):
        operation = "retrieve matching records"
    elif "sync_objects_to_snowflake" in action_name:
        operation = "store records in a database table"
    elif "update" in action_name:
        operation = "update records"
    elif "upsert" in action_name:
        operation = "create or update records"
    elif action_name.startswith(("add_", "create_")):
        operation = "add a record"
    elif "delete" in action_name:
        operation = "delete records"
    elif is_slack_message:
        operation = (
            "post a Slack reply"
            if benchmark_tool == "slack.post_reply"
            else "post or update a Slack message"
        )
    elif action_name.startswith(("send_", "post_")):
        operation = "send the configured communication"
    elif "parse_json" in action_name:
        operation = "parse the supplied JSON"
    else:
        operation = _human(action_name)
    target = (
        custom_sql_effect[2]
        if custom_sql_effect is not None and custom_sql_effect[0] != "select"
        else ""
    )
    if not target:
        for key in (
            "sobject_name",
            "lookup_table_id",
            "table_id",
            "table",
            "spreadsheet",
            "sheet",
            "object_name",
            "object",
        ):
            dynamic_value = _display_dynamic_value(dynamic.get(key))
            value = dynamic_value or args.get(key)
            if value not in (None, ""):
                target = str(value).strip()
                break
    if not target and "sql" in args:
        table_match = re.search(
            r"\bFROM\s+([A-Za-z0-9_.\"`]+)",
            str(args.get("sql") or ""),
            flags=re.I,
        )
        if table_match:
            target = table_match.group(1).strip('"`')
    service_name = (
        _display_dynamic_value(dynamic.get("flow_id"))
        if is_callable_service
        else ""
    )
    service_id = str(args.get("flow_id") or "").strip()
    if is_callable_service and service_name:
        description = f"Use the {service_name} business service"
        if service_id:
            description += f' identified by "{service_id}"'
        description += "."
    elif is_slack_message:
        description = operation[:1].upper() + operation[1:] + "."
    elif is_adhoc_http:
        raw_verb = str(args.get("verb") or "").strip()
        method = (
            raw_verb.upper()
            if re.fullmatch(r"[A-Za-z]+", raw_verb)
            else "configured-method"
        )
        request_path = str(args.get("path") or "").strip()
        description = f"Send an HTTP {method} request"
        if request_path:
            description += f" to {json.dumps(request_path, ensure_ascii=False)}"
        description += "."
    else:
        description = (
            f"Perform {operation}"
            + (f" for {target}" if target else "")
            + "."
        )
    if is_slack_message:
        advanced = args.get("advanced") or {}
        if isinstance(advanced, dict) and advanced.get("ts") not in (None, ""):
            update_source = _formula_value_summary(
                advanced.get("ts"), nodes_by_as
            ) or _semantic_scalar(advanced.get("ts"), "unknown")
            update_source = _business_binding_source(update_source)
            description += (
                f" Update the existing Slack message identified by "
                f"{update_source}."
            )
        if (
            isinstance(advanced, dict)
            and advanced.get("thread_ts") not in (None, "")
        ):
            thread_source = _formula_value_summary(
                advanced.get("thread_ts"), nodes_by_as
            ) or _semantic_scalar(advanced.get("thread_ts"), "unknown")
            thread_source = _business_binding_source(thread_source)
            description += f" Post it in the Slack thread selected from {thread_source}."
    if mappings:
        if is_adhoc_http:
            binding_intro = " Build it with: "
        elif is_slack_message or is_callable_service:
            binding_intro = " Apply these business bindings: "
        else:
            binding_intro = " Preserve these configured mappings: "
        description += binding_intro + "; ".join(
            f"{field} from {source}" for field, source in mappings
        ) + "."
    if slack_lifecycle_labels:
        description += (
            " Preserve these exact visible Slack labels: "
            + ", ".join(
                json.dumps(label, ensure_ascii=False)
                for label in slack_lifecycle_labels
            )
            + "."
        )
    raw_limit = args.get("limit")
    normalized_limit = str(raw_limit or "").replace(",", "").strip()
    if re.fullmatch(r"[0-9]+", normalized_limit) and int(
        normalized_limit
    ) > 0:
        description += (
            f" Return at most {int(normalized_limit):,} matching records."
        )
    order = str(
        args.get("order_direction")
        or args.get("sort_direction")
        or ""
    ).lower()
    if order in {"asc", "ascending", "desc", "descending"}:
        description += (
            " Return them in "
            + (
                "ascending"
                if order in {"asc", "ascending"}
                else "descending"
            )
            + " order."
        )
    if "update_only" in args and (
        custom_sql_effect is None or custom_sql_effect[0] == "select"
    ):
        update_only = str(args.get("update_only") or "").lower()
        if update_only == "false":
            description += " Permit read-only query execution."
        elif update_only == "true":
            description += " Permit only statements that update data."
    if "ignore_not_found" in args:
        ignore = str(args.get("ignore_not_found") or "").lower()
        if ignore == "false":
            description += " Treat a missing target record as an error."
        elif ignore == "true":
            description += " Do not fail when the target record is absent."
    advanced = args.get("advanced_configuration") or {}
    if (
        isinstance(advanced, dict)
        and str(advanced.get("allOrNone") or "").lower() == "false"
    ):
        description += (
            " Each record may succeed or fail independently rather than "
            "rolling back the whole collection."
        )
    category = (
        "required_outputs"
        if "generate_menu_options" in action_name
        else "data_transformations"
    )
    anchors = [
        [service_name if is_callable_service and service_name else operation],
        *([[service_id]] if is_callable_service and service_id else []),
        *([[target, _human(target)]] if target else []),
        *[[field] for field, _ in mappings],
        *[
            [source]
            for _, source in mappings
            if not source.startswith(('"', "{", "["))
        ],
        *[[label] for label in slack_lifecycle_labels],
        *(
            [[f"at most {int(normalized_limit):,}"]]
            if re.fullmatch(r"[0-9]+", normalized_limit)
            and int(normalized_limit) > 0
            else []
        ),
    ]
    return description, anchors, category


def _action_effect_visibility(node: dict[str, Any]) -> tuple[str, bool]:
    """Classify pure runtime plumbing separately from task-visible effects.

    Parsing connector output and accumulating an internal working list are
    ways to implement a later business effect.  Their downstream observable
    message/update/result remains visible through that later action, but the
    parser invocation, sample schema, accumulator name, and working-list
    schema are not requirements a task author would state in Q.
    """

    action = str(node.get("recipe_action") or "").lower()
    benchmark_tool = str(node.get("benchmark_tool") or "").lower()
    if any(
        marker in action or marker in benchmark_tool
        for marker in _IMPLEMENTATION_ONLY_TRANSFORM_ACTION_MARKERS
    ):
        return "implementation_only", False
    return "user_visible", True


def _formula_effect_visibility(node: dict[str, Any]) -> tuple[str, bool]:
    base_visibility = _action_effect_visibility(node)
    if base_visibility[1] is False:
        return base_visibility
    if (
        str(node.get("recipe_action") or "")
        == "workato_service.call_service"
        and any(
            str(reference.get("pill_type") or "") == "job_context"
            for reference in references(
                node.get("configured_arguments") or {}
            )
        )
    ):
        return "implementation_only", False
    return base_visibility


def _output_field_description(
    field: str,
    value: Any,
    nodes_by_as: dict[str, dict[str, Any]],
) -> tuple[str, list[list[str]]]:
    """Describe one reply field without connector- or recipe-specific cases."""

    field_name = _human(field)
    anchors: list[list[str]] = [[field, field_name]]
    if isinstance(value, dict) and "____source" in value:
        item_fields = [
            str(key) for key in value if not str(key).startswith("____")
        ]
        anchors.extend([[name, _human(name)] for name in item_fields])
        return (
            f"Success output {field} is an array whose items contain the "
            f"exact fields {', '.join(item_fields)}.",
            anchors,
        )
    serialized = json.dumps(value, ensure_ascii=False)
    if isinstance(value, str) and "smart_join" in value:
        separator_match = re.search(
            r"smart_join\([\"'](?P<separator>.*?)[\"']\)",
            value,
            flags=re.S,
        )
        separator = (
            separator_match.group("separator")
            if separator_match
            else "the configured separator"
        )
        pluck_match = re.search(r"\.pluck\([\"'](?P<field>.*?)[\"']\)", value)
        selected = (
            _human(pluck_match.group("field"))
            if pluck_match
            else "selected source"
        )
        anchors.extend([[selected], [separator]])
        return (
            f"Success output {field} joins the {selected} values in source "
            f"order with {separator!r}.",
            anchors,
        )
    if (
        isinstance(value, str)
        and (
            '"path_element_type": "size"' in value
            or "'path_element_type': 'size'" in value
            or "____Size" in value
        )
    ):
        labels = _formula_labels(value, nodes_by_as)
        anchors.append(["count", "number"])
        return (
            f"Success output {field} is the count of "
            f"{', '.join(labels) if labels else 'the referenced rows'}.",
            anchors,
        )
    labels = _formula_labels(value, nodes_by_as)
    if labels:
        anchors.extend([[label] for label in labels])
        return (
            f"Success output {field} comes from "
            f"{', '.join(labels)}.",
            anchors,
        )
    return (
        f"Success output {field} is the configured value "
        f"{serialized}.",
        anchors,
    )


def _path_controller_ids(node: dict[str, Any]) -> set[str]:
    return {
        str(item.get("controller") or "")
        for item in node.get("path_conditions") or []
        if isinstance(item, dict) and item.get("controller")
    }


def _conditionally_unavailable_reply_fields(
    reply_node: dict[str, Any],
    nodes_by_as: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Infer reply defaults when a referenced branch-local producer is absent."""

    fields = _reply_fields(reply_node.get("configured_arguments") or {})
    reply_controllers = _path_controller_ids(reply_node)
    result: dict[str, Any] = {}
    for field, value in fields.items():
        refs = references(value)
        has_branch_local_source = any(
            (
                source := nodes_by_as.get(str(ref.get("line") or ""))
            )
            is not None
            and bool(_path_controller_ids(source) - reply_controllers)
            for ref in refs
        )
        explicit_nil = (
            isinstance(value, str)
            and bool(re.search(r"\b(?:else\s+)?nil\b", value, flags=re.I))
        )
        if isinstance(value, dict) and "____source" in value:
            if has_branch_local_source:
                result[str(field)] = []
        elif explicit_nil or has_branch_local_source:
            result[str(field)] = None
    return result


def _null_record_reply_fields(
    reply_node: dict[str, Any],
    nodes_by_as: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    """Return reply fields that dereference a nullable single-record read.

    A successful ``lookup_table.get_entry`` call can return ``entry: null``.
    Workato still constructs the configured success reply in that case, and
    every scalar path below the missing entry is present with a null value.
    Keep this distinct from a conditionally skipped producer: the read action
    did execute, but its record value is null.
    """

    fields = _reply_fields(reply_node.get("configured_arguments") or {})
    result: dict[str, Any] = {}
    source_ids: list[str] = []
    for field, value in fields.items():
        for reference in references(value):
            source = nodes_by_as.get(str(reference.get("line") or ""))
            if source is None:
                continue
            action = str(source.get("recipe_action") or "")
            tool = str(source.get("benchmark_tool") or "")
            path = reference.get("path") or []
            if (
                action != "lookup_table.get_entry"
                and tool != "lookup_table.get_entry"
            ):
                continue
            if not path or str(path[0]) != "entry" or len(path) < 2:
                continue
            result[str(field)] = None
            source_id = str(source.get("node_id") or "")
            if source_id and source_id not in source_ids:
                source_ids.append(source_id)
            break
    return result, source_ids


def _branch_local_reply_conditions(
    reply_node: dict[str, Any],
    nodes_by_as: dict[str, dict[str, Any]],
    nodes_by_id: dict[str, dict[str, Any]],
) -> list[tuple[str, str]]:
    """Return controller IDs/descriptions for reply inputs made in a branch."""

    reply_controllers = _path_controller_ids(reply_node)
    found: list[tuple[str, str]] = []
    fields = _reply_fields(reply_node.get("configured_arguments") or {})
    for ref in references(fields):
        source = nodes_by_as.get(str(ref.get("line") or ""))
        if source is None:
            continue
        for controller_id in sorted(
            _path_controller_ids(source) - reply_controllers
        ):
            controller = nodes_by_id.get(controller_id)
            if controller is None:
                continue
            description, _ = _condition_description(
                controller.get("condition") or "the branch condition",
                nodes_by_as,
            )
            pair = (controller_id, description)
            if pair not in found:
                found.append(pair)
    return found


def extract_semantic_ledger(workflow_a: dict[str, Any]) -> dict[str, Any]:
    """Extract source-grounded semantic facts directly from A.

    This function deliberately has no inputs for C, P, Q, or model output.
    """
    ledger: dict[str, list[dict[str, Any]]] = {
        category: [] for category in LEDGER_CATEGORIES
    }
    trigger = workflow_a.get("trigger", {})
    public_fields = public_input_facts(trigger)
    for field in public_fields:
        name = str(field.get("name") or "")
        label = str(field.get("label") or _human(name))
        path_parts = [
            str(part)
            for part in (field.get("path") or [name])
            if str(part)
        ]
        path = _display_path(path_parts)
        field_type = str(field.get("type") or "unknown")
        description = (
            (
                f"Public input {path} is required, has type "
                f"{field_type}, and has label {label}."
            )
            if field.get("required")
            else f"Public input {path} has label {label}."
        )
        _add(
            ledger,
            "public_inputs",
            description=description,
            evidence=[
                "workflow_A.trigger."
                + str(field.get("source") or "public_inputs")
                + "."
                + path
            ],
            anchors=[[path, _human(name), label.lower()]],
        )

    all_nodes = workflow_a.get("nodes") or []
    reachable = control_flow_reachable_node_ids(workflow_a)
    ignored_unreachable_action_node_ids = [
        str(node.get("node_id") or "")
        for node in all_nodes
        if node.get("source_keyword") == "action"
        and str(node.get("node_id") or "") not in reachable
    ]
    ignored_unreachable_terminal_node_ids = [
        str(node.get("node_id") or "")
        for node in all_nodes
        if (node.get("terminal") or {}).get("is_terminal") is True
        and str(node.get("node_id") or "") not in reachable
    ]
    ignored_skipped_node_ids = [
        str(node.get("node_id") or "")
        for node in all_nodes
        if node.get("skip") is True
    ]
    ignored_unreachable_node_ids = set(
        ignored_unreachable_action_node_ids
        + ignored_unreachable_terminal_node_ids
        + ignored_skipped_node_ids
    )
    nodes = task_effect_nodes(workflow_a)
    returned_response_statuses = {
        str(
            (node.get("configured_arguments") or {}).get(
                "http_status_code"
            )
            or ""
        )
        for node in nodes
        if str(node.get("recipe_action") or "")
        == "workato_api_platform.return_response"
    }
    returned_response_statuses.discard("")

    trigger_response = (
        trigger
        .get("configured_input", {})
        .get("response")
    )
    if isinstance(trigger_response, dict):
        content_type = str(trigger_response.get("content_type") or "")
        responses = [
            item
            for item in trigger_response.get("responses") or []
            if isinstance(item, dict)
        ]
        for response in responses:
            name = str(response.get("name") or "")
            status = str(response.get("http_status_code") or "")
            if status not in returned_response_statuses:
                continue
            parts = [
                value
                for value in (
                    f"named {name}" if name else "",
                    f"with HTTP status {status}" if status else "",
                    f"and {content_type.upper()} content type"
                    if content_type
                    else "",
                )
                if value
            ]
            _add(
                ledger,
                "required_outputs",
                description=(
                    "After processing the API request, return the configured "
                    "response " + " ".join(parts) + "."
                ),
                evidence=[
                    "workflow_A.trigger.configured_input.response",
                ],
                anchors=[
                    *([[name.lower()]] if name else []),
                    *([[status]] if status else []),
                    *([[content_type.lower()]] if content_type else []),
                    ["return", "respond", "response"],
                ],
            )

    seen_entities: set[str] = set()
    nodes_by_as = {
        str(node.get("source_as") or ""): node
        for node in nodes
        if node.get("source_as")
    }
    nodes_by_id = {
        str(node.get("node_id") or ""): node
        for node in nodes
        if node.get("node_id")
    }
    trigger_predicate = trigger.get("predicate")
    if isinstance(trigger_predicate, dict) and trigger_predicate:
        predicate_description, predicate_anchors = _condition_description(
            trigger_predicate,
            nodes_by_as,
        )
        _add(
            ledger,
            "configured_filters",
            description=(
                "The source trigger accepts the event only when "
                f"{predicate_description}."
            ),
            evidence=["workflow_A.trigger.predicate"],
            anchors=predicate_anchors
            or [["source trigger", "trigger predicate", "prefilter"]],
            visibility="implementation_only",
            required_in_q=False,
        )
    for node in nodes:
        node_id = str(node["node_id"])
        args = node.get("configured_arguments") or {}
        action = str(node.get("recipe_action") or "")
        object_name = args.get("sobject_name")
        if isinstance(object_name, str) and object_name not in seen_entities:
            seen_entities.add(object_name)
            words = _human(object_name)
            _add(
                ledger,
                "domain_entities",
                description=f"Salesforce entity {object_name}.",
                evidence=[
                    f"workflow_A.nodes.{node_id}.configured_arguments.sobject_name"
                ],
                anchors=[[words, object_name]],
            )

        action_effect = _action_effect_description(node, nodes_by_as)
        if action_effect is not None:
            effect_description, effect_anchors, effect_category = action_effect
            effect_visibility, effect_required = _action_effect_visibility(node)
            _add(
                ledger,
                effect_category,
                description=effect_description,
                evidence=[
                    f"workflow_A.nodes.{node_id}.recipe_action",
                    f"workflow_A.nodes.{node_id}.configured_arguments",
                    f"workflow_A.nodes.{node_id}.input_schema",
                ],
                anchors=effect_anchors,
                visibility=effect_visibility,
                required_in_q=effect_required,
            )
        for filter_description, filter_anchors in _configured_action_filters(
            node,
            nodes_by_as,
        ):
            _add(
                ledger,
                "configured_filters",
                description=filter_description,
                evidence=[
                    f"workflow_A.nodes.{node_id}.configured_arguments.filters",
                    (
                        f"workflow_A.nodes.{node_id}."
                        "dynamic_pick_list_selection"
                    ),
                ],
                anchors=filter_anchors,
            )
        for formula_description, formula_anchors in _formula_effects(
            node, nodes_by_as
        ):
            formula_visibility, formula_required = _formula_effect_visibility(node)
            _add(
                ledger,
                "data_transformations",
                description=formula_description,
                evidence=[
                    f"workflow_A.nodes.{node_id}.configured_arguments",
                ],
                anchors=formula_anchors,
                visibility=formula_visibility,
                required_in_q=formula_required,
            )

        # A Slack thread timestamp can carry a nested ``presence or`` fallback
        # under advanced.thread_ts.  The old Salesforce-only top-level scan
        # missed this observable choice and left Q with an ambiguous rule.
        if str(node.get("benchmark_tool") or "") == "slack.post_message":
            for fallback_path, fallback_value in _walk_leaf_values(args):
                if not (
                    isinstance(fallback_value, str)
                    and fallback_value.lstrip().startswith("=")
                    and " or " in fallback_value
                    and ".presence" in fallback_value.lower()
                    and fallback_path
                    and fallback_path[-1] == "thread_ts"
                ):
                    continue
                alternatives = _formula_labels(fallback_value, nodes_by_as)
                if len(alternatives) < 2:
                    continue
                alternatives = [
                    _business_binding_source(value)
                    for value in alternatives
                ]
                rule = (
                    f"Use {alternatives[0]} only when it is neither null "
                    "nor false, empty, or whitespace-only; otherwise use "
                    f"{alternatives[1]}."
                )
                _add(
                    ledger,
                    "fallback_rules",
                    description=f"Resolve Slack thread: {rule}",
                    evidence=[
                        "workflow_A.nodes."
                        f"{node_id}.configured_arguments."
                        + ".".join(fallback_path)
                    ],
                    anchors=[
                        [
                            "neither null nor false, empty, or whitespace-only",
                            "otherwise",
                        ],
                        *[[name] for name in alternatives],
                    ],
                )

        condition = node.get("condition")
        if isinstance(condition, dict) and condition:
            description, anchors = _condition_description(
                condition,
                nodes_by_as,
            )
            _add(
                ledger,
                "configured_filters",
                description=f"Branch condition: {description}.",
                evidence=[f"workflow_A.nodes.{node_id}.condition"],
                anchors=anchors,
            )
            outgoing = [
                edge
                for edge in workflow_a.get("control_flow_edges") or []
                if str(edge.get("from")) == node_id
            ]
            has_true = any(
                edge.get("edge_type") == "condition_true"
                for edge in outgoing
            )
            has_false = any(
                edge.get("edge_type") == "condition_false"
                for edge in outgoing
            )
            if (
                node.get("source_keyword") in {"if", "elsif"}
                and has_true
                and not has_false
            ):
                _add(
                    ledger,
                    "terminal_rules",
                    description=(
                        f"When the condition is false ({description}), execute "
                        "no true-branch action and end through normal "
                        "fall-through."
                    ),
                    evidence=[
                        f"workflow_A.nodes.{node_id}.condition",
                        "workflow_A.control_flow_edges",
                    ],
                    anchors=[
                        ["otherwise", "when false", "if not", "when absent"],
                        [
                            "perform no further actions",
                            "do not search",
                            "do not update",
                            "send no result",
                            "no reply",
                            "end processing",
                        ],
                    ],
                )

        custom_sql_effect = _custom_sql_effect(node)
        custom_sql_has_predicate = (
            custom_sql_effect is not None
            and custom_sql_effect[0] in {"select", "update", "delete", "merge"}
            and re.search(
                r"\b(?:WHERE|ON)\b",
                str(args.get("sql") or ""),
                flags=re.I,
            )
            is not None
        )
        configured_predicate = (
            args.get("conditions")
            if isinstance(args.get("conditions"), str)
            else args.get("query")
            if (
                action.startswith("salesforce.")
                or "search_rows_sql" in action
            )
            and isinstance(args.get("query"), str)
            else args.get("sql")
            if (
                "search_rows_sql" in action
                or custom_sql_has_predicate
            )
            and isinstance(args.get("sql"), str)
            else None
        )
        if configured_predicate:
            trigger_prefilter = (
                node.get("kind") == "trigger"
                and not node.get("benchmark_tool")
            )
            predicate_description, predicate_anchors = (
                _configured_query_filter(
                    configured_predicate,
                    nodes_by_as,
                )
            )
            if custom_sql_effect is not None:
                predicate_description = predicate_description.replace(
                    "Select records",
                    {
                        "update": "Apply the update to records",
                        "delete": "Delete records",
                        "merge": "Match records for the create-or-update operation",
                    }.get(custom_sql_effect[0], "Select records"),
                    1,
                )
            _add(
                ledger,
                "configured_filters",
                description=(
                    (
                        "The source trigger prefilters records using this "
                        "implementation-only condition. "
                        if trigger_prefilter
                        else ""
                    )
                    + predicate_description
                ),
                evidence=[
                    f"workflow_A.nodes.{node_id}.configured_arguments."
                    + (
                        "conditions"
                        if isinstance(args.get("conditions"), str)
                        else "query"
                        if isinstance(args.get("query"), str)
                        else "sql"
                    )
                ],
                anchors=predicate_anchors
                or [["record selection", "filter", "predicate"]],
                visibility=(
                    "implementation_only"
                    if trigger_prefilter
                    else "user_visible"
                ),
                required_in_q=not trigger_prefilter,
            )

        if action.startswith("salesforce.search_sobjects"):
            if not configured_predicate:
                for key, value in args.items():
                    if key in _SEARCH_METADATA:
                        continue
                    labels = _formula_labels(value, nodes_by_as)
                    if labels:
                        value_description = ", then ".join(labels)
                    elif (
                        isinstance(value, str)
                        and value.lower() in {"true", "false", "null"}
                    ):
                        value_description = (
                            f'the string "{value.lower()}"'
                        )
                    else:
                        value_description = json.dumps(
                            value, ensure_ascii=False, sort_keys=True
                        )
                    _add(
                        ledger,
                        "configured_filters",
                        description=(
                            f"Filter {object_name or 'the Salesforce entity'} "
                            f"where {key} equals {value_description}."
                        ),
                        evidence=[
                            f"workflow_A.nodes.{node_id}."
                            f"configured_arguments.{key}"
                        ],
                        anchors=[
                            [key, _human(key)],
                            *([[str(value).lower()]] if not labels else []),
                            *(
                                [["string", f'"{value.lower()}"']]
                                if isinstance(value, str)
                                and value.lower()
                                in {"true", "false", "null"}
                                else []
                            ),
                            *[[label] for label in labels],
                        ],
                    )
            fields = _selected_field_entries(args)
            if fields:
                _add(
                    ledger,
                    "data_transformations",
                    description=(
                        f"Retrieve fields {', '.join(fields)} from "
                        f"{object_name or 'the Salesforce entity'}."
                    ),
                    evidence=[
                        f"workflow_A.nodes.{node_id}.configured_arguments.field_list"
                    ],
                    anchors=[[value, _human(value)] for value in fields],
                    visibility="plan_visible",
                    required_in_q=False,
                )
            raw_limit = args.get("limit")
            normalized_limit = str(raw_limit).replace(",", "").strip()
            result_limit = (
                int(normalized_limit)
                if re.fullmatch(r"[0-9]+", normalized_limit)
                else 0
            )
            if result_limit > 0:
                _add(
                    ledger,
                    "data_transformations",
                    description=(
                        "Return at most "
                        f"{result_limit:,} "
                        f"{'record' if result_limit == 1 else 'records'} "
                        "from this search."
                    ),
                    evidence=[
                        f"workflow_A.nodes.{node_id}."
                        "configured_arguments.limit"
                    ],
                    anchors=[
                        [
                            f"at most {result_limit}",
                            f"at most {result_limit:,}",
                            f"up to {result_limit}",
                            f"up to {result_limit:,}",
                            *(
                                ["a single record", "one record"]
                                if result_limit == 1
                                else []
                            ),
                        ]
                    ],
                )
            for key, value in args.items():
                if (
                    isinstance(value, str)
                    and value.lstrip().startswith("=")
                    and " or " in value
                ):
                    alternatives = _formula_labels(value, nodes_by_as)
                    if len(alternatives) < 2:
                        continue
                    _add(
                        ledger,
                        "fallback_rules",
                        description=(
                            f"Resolve {_human(key)} using Ruby `or` semantics "
                            "in this order: "
                            f"{', '.join(alternatives)}. Select the first "
                            "value that is neither false nor null; retain "
                            "blank strings rather than skipping them."
                        ),
                        evidence=[
                            f"workflow_A.nodes.{node_id}.configured_arguments.{key}"
                        ],
                        anchors=[
                            [
                                "first value that is neither false nor null",
                                "false nor null",
                                "blank string is not skipped",
                                "blank strings are retained",
                                "fallback",
                                "otherwise",
                                "precedence",
                                "in this order",
                            ],
                            *[[name] for name in alternatives],
                        ],
                    )

        if action == "workato_smart_list.query_list":
            sql = str(args.get("sql") or "")
            upper = sql.upper()
            if "CREATE TABLE" in upper or "INSERT INTO" in upper:
                column_match = re.search(
                    r"(?:CREATE\s+TABLE\s+\S+\s*\(|INSERT\s+INTO\s+\S+\s*\()"
                    r"(?P<columns>[^)]+)\)",
                    sql,
                    flags=re.I | re.S,
                )
                columns = [
                    value.strip().split()[0].strip('"`[]')
                    for value in (
                        column_match.group("columns").split(",")
                        if column_match
                        else []
                    )
                    if value.strip()
                ]
                _add(
                    ledger,
                    "data_transformations",
                    description=(
                        "Materialize configured values in an internal working "
                        "list"
                        + (
                            f" with columns {', '.join(columns)}."
                            if columns
                            else "."
                        )
                    ),
                    evidence=[
                        f"workflow_A.nodes.{node_id}.configured_arguments.sql"
                    ],
                    anchors=[[value, _human(value)] for value in columns],
                    visibility="implementation_only",
                    required_in_q=False,
                )
            window_match = re.search(
                r"\bROW_NUMBER\s*\(\s*\)\s+OVER\s*\(\s*"
                r"PARTITION\s+BY\s+(?P<partition>.*?)\s+"
                r"ORDER\s+BY\s+(?P<field>\"[^\"]+\"|`[^`]+`|"
                r"\[[^\]]+\]|[A-Za-z0-9_.]+)\s+"
                r"(?P<direction>ASC|DESC)\s*\)\s+AS\s+"
                r"(?P<alias>[A-Za-z0-9_]+)",
                sql,
                flags=re.I | re.S,
            )
            retains_first = bool(
                window_match
                and re.search(
                    rf"\bWHERE\s+{re.escape(window_match.group('alias'))}"
                    r"\s*=\s*1\b",
                    sql,
                    flags=re.I,
                )
            )
            if window_match and retains_first:
                partition_fields = [
                    _human(next(value for value in match.groups() if value))
                    for match in re.finditer(
                        r'"([^\"]+)"|`([^`]+)`|\[([^\]]+)\]|'
                        r"([A-Za-z0-9_.]+)",
                        window_match.group("partition"),
                    )
                ]
                order_field = window_match.group("field").strip('"`[]')
                direction = window_match.group("direction").lower()
                _add(
                    ledger,
                    "data_transformations",
                    description=(
                        "Within each group of working rows sharing "
                        + " and ".join(partition_fields)
                        + f", order rows by {_human(order_field)} "
                        + (
                            "ascending"
                            if direction == "asc"
                            else "descending"
                        )
                        + " and retain only the first row."
                    ),
                    evidence=[
                        f"workflow_A.nodes.{node_id}.configured_arguments.sql"
                    ],
                    anchors=[
                        *[[field] for field in partition_fields],
                        [order_field, _human(order_field)],
                        [
                            direction,
                            *(
                                ["earliest to latest", "ascending"]
                                if direction == "asc"
                                else ["latest to earliest", "descending"]
                            ),
                        ],
                        ["retain first", "first row", "deduplicate"],
                    ],
                )
            else:
                order_match = re.search(
                    r"\bORDER\s+BY\s+(?P<field>\"[^\"]+\"|`[^`]+`|"
                    r"\[[^\]]+\]|[A-Za-z0-9_.]+)"
                    r"(?:\s+(?P<direction>ASC|DESC))?",
                    sql,
                    flags=re.I,
                )
            if not (window_match and retains_first) and order_match:
                order_field = order_match.group("field").strip('"`')
                direction = (order_match.group("direction") or "ASC").lower()
                _add(
                    ledger,
                    "data_transformations",
                    description=(
                        f"Sort the working rows by {_human(order_field)} "
                        f"{'ascending' if direction == 'asc' else 'descending'}."
                    ),
                    evidence=[
                        f"workflow_A.nodes.{node_id}.configured_arguments.sql"
                    ],
                    anchors=[
                        [order_field, _human(order_field)],
                        [
                            direction,
                            *(
                                ["earliest to latest", "ascending"]
                                if direction == "asc"
                                else ["latest to earliest", "descending"]
                            ),
                        ],
                    ],
                )

        if action in {"logger.log_message", "workato_runtime.log_message"}:
            message = str(args.get("message") or "")
            if "gsub" in message and ("''" in message or "\\'" in message):
                _add(
                    ledger,
                    "data_transformations",
                    description=(
                        "Escape apostrophes in a value before inserting it "
                        "into the internal working list."
                    ),
                    evidence=[
                        f"workflow_A.nodes.{node_id}.configured_arguments.message"
                    ],
                    anchors=[["apostrophe", "escape"]],
                    visibility="implementation_only",
                    required_in_q=False,
                )
            else:
                message_names = _path_names(message)
                message_sources = _formula_labels(message, nodes_by_as)
                loop_message = any(
                    marker in message
                    for marker in ("foreach", "current_item")
                )
                if message_sources:
                    message_description = (
                        (
                            "For each loop item, log one message"
                            if loop_message
                            else "Log one message"
                        )
                        + " using "
                        + ", then ".join(message_sources)
                        + ", preserving the configured literal text, "
                        "punctuation, and separators."
                    )
                else:
                    message_description = (
                        "For each loop item, log one message using the configured "
                        f"text pattern {message!r}."
                        if loop_message
                        else (
                            "Log one message using the configured text pattern "
                            f"{message!r}."
                        )
                    )
                split_by_index = re.search(
                    r"\.split\(\s*(['\"])(?P<delimiter>.*?)\1\s*\)"
                    r"\s*\[.*?foreach.*?index",
                    message,
                    flags=re.I,
                )
                if split_by_index:
                    source = (
                        message_sources[0]
                        if message_sources
                        else "the source text"
                    )
                    delimiter = split_by_index.group("delimiter")
                    message_description = (
                        "For each loop item, log the corresponding entry "
                        f"selected by splitting {source} on {delimiter!r} and "
                        "taking the entry at that item's iteration index."
                    )
                elif (
                    "foreach_meta" in message
                    and "index" in message
                    and re.search(r"hi:\s*", message, flags=re.I)
                ):
                    message_description = (
                        "For each loop item, log one message containing the "
                        "literal text 'hi: ' followed by that item's iteration "
                        "index."
                    )
                _add(
                    ledger,
                    "data_transformations",
                    description=message_description,
                    evidence=[
                        f"workflow_A.nodes.{node_id}.configured_arguments.message"
                    ],
                    anchors=[
                        ["log", "record a log message", "write a log message"],
                        *[[value] for value in message_names],
                        *[[value] for value in message_sources],
                        *(
                            [["iteration index", "item index"]]
                            if "index" in message
                            else []
                        ),
                    ],
                )

        if action == "workato_api_platform.return_response":
            response_fields = args.get("response")
            if isinstance(response_fields, dict):
                for field, value in response_fields.items():
                    description, anchors = _output_field_description(
                        str(field), value, nodes_by_as
                    )
                    if (
                        isinstance(value, str)
                        and "_dp(" not in value
                        and value.lower() in {"true", "false", "null"}
                    ):
                        description = (
                            f"Response field {field} is the JSON string "
                            f"{value!r}, not a boolean or null value."
                        )
                        anchors.append(
                            ["string", f'"{value}"', f"'{value}'"]
                        )
                    _add(
                        ledger,
                        "required_outputs",
                        description=description.replace(
                            "Success output", "Response output", 1
                        ),
                        evidence=[
                            (
                                f"workflow_A.nodes.{node_id}"
                                f".configured_arguments.response.{field}"
                            )
                        ],
                        anchors=anchors,
                    )

        if action == "workato_service.send_reply":
            reply_type = str(args.get("reply_type") or "")
            fields = _reply_fields(args)
            if reply_type == "success" and fields:
                for field, value in fields.items():
                    serialized = json.dumps(value, ensure_ascii=False)
                    description, anchors = _output_field_description(
                        str(field), value, nodes_by_as
                    )
                    _add(
                        ledger,
                        "required_outputs",
                        description=description,
                        evidence=[
                            f"workflow_A.nodes.{node_id}.configured_arguments.reply.{field}"
                        ],
                        anchors=anchors,
                    )
                    formula_semantics = node.get("formula_semantics") or {}
                    lookup_semantics = formula_semantics.get("lookup") or {}
                    if (
                        "lookup(" in serialized
                        and "no_matching_row_or_field" in lookup_semantics
                        and lookup_semantics["no_matching_row_or_field"] is None
                    ):
                        _add(
                            ledger,
                            "required_outputs",
                            description=(
                                f"When the lookup for output field {field} has "
                                f"no matching row or selected field, return "
                                f"success with {field} set to null."
                            ),
                            evidence=[
                                f"workflow_A.nodes.{node_id}."
                                f"configured_arguments.reply.{field}",
                                f"workflow_A.nodes.{node_id}."
                                "formula_semantics.lookup",
                            ],
                            anchors=[
                                [
                                    "no matching region",
                                    "no matching row",
                                    "lookup has no match",
                                    "lookup finds no match",
                                ],
                                [f"{field} null", f"{field} is null"],
                                ["success"],
                            ],
                        )
            elif reply_type == "error":
                message = str(args.get("message") or "")
                is_exception = any(
                    item.get("branch") == "exception"
                    for item in node.get("path_conditions") or []
                )
                if not is_exception:
                    message_words = [
                        value
                        for value in _words(message)
                        if len(value) > 2
                        and value
                        not in {
                            "the",
                            "and",
                            "from",
                            "with",
                            "either",
                            "please",
                            "provide",
                        }
                    ]
                    _add(
                        ledger,
                        "validation_errors",
                        description=(
                            f"Return an error with message: {message}"
                        ),
                        evidence=[
                            f"workflow_A.nodes.{node_id}.configured_arguments"
                        ],
                        anchors=[
                            ["error"],
                            *[[value] for value in message_words[:8]],
                        ],
                    )

        terminal = node.get("terminal") or {}
        if terminal.get("is_terminal"):
            mechanism = str(terminal.get("mechanism") or "")
            path_conditions = node.get("path_conditions") or []
            terminal_condition = ""
            terminal_anchors: list[list[str]] = []
            if path_conditions:
                last_path = path_conditions[-1]
                expression = last_path.get("expression") or {}
                condition_text, condition_anchors = _condition_description(
                    expression,
                    nodes_by_as,
                )
                branch = str(last_path.get("branch") or "selected")
                terminal_condition = (
                    f" on the {branch} path for: {condition_text}"
                )
                terminal_anchors = condition_anchors
            if mechanism == "explicit_stop":
                stop_reason = str(args.get("stop_reason") or "")
                stop_reason_labels = _formula_labels(
                    stop_reason,
                    nodes_by_as,
                )
                visible_stop_reason = (
                    ", then ".join(stop_reason_labels)
                    if stop_reason_labels
                    else stop_reason
                )
                stop_with_error = str(
                    args.get("stop_with_error") or ""
                ).lower() == "true"
                if stop_reason:
                    description = (
                        "End processing "
                        + ("as an error " if stop_with_error else "")
                        + f'with reason "{visible_stop_reason}"'
                        + f"{terminal_condition}; this stop does not emit "
                        "an API response."
                    )
                else:
                    description = (
                        "End processing when the explicit stop is reached"
                        f"{terminal_condition}."
                    )
                visibility = "user_visible"
                required_in_q = True
                terminal_words = [
                    "stop",
                    "end processing",
                    "do not continue",
                    "halt",
                ]
                if stop_reason:
                    terminal_words.extend(
                        [
                            visible_stop_reason,
                            "do not send an API response",
                        ]
                    )
            elif mechanism == "inherent_action_termination":
                description = (
                    f"{action} returns its response and inherently ends "
                    "processing."
                )
                visibility = "user_visible"
                required_in_q = True
                terminal_words = [
                    "return",
                    "respond",
                    "end processing",
                    "immediately",
                ]
            else:
                description = f"Recipe-terminal action uses {mechanism}."
                visibility = "implementation_only"
                required_in_q = False
                terminal_words = ["terminal", "ends the recipe"]
            _add(
                ledger,
                "terminal_rules",
                description=description,
                evidence=[
                    f"workflow_A.nodes.{node_id}.terminal",
                    *(
                        [f"workflow_A.nodes.{node_id}.path_conditions"]
                        if path_conditions
                        else []
                    ),
                ],
                anchors=[terminal_words, *terminal_anchors],
                visibility=visibility,
                required_in_q=required_in_q,
                    )

    for region_index, region in enumerate(
        workflow_a.get("exception_regions") or [],
        start=1,
    ):
        protected_nodes = [
            nodes_by_id[node_id]
            for node_id in region.get("protected_node_ids") or []
            if node_id in nodes_by_id
        ]
        if not protected_nodes:
            continue
        catch_nodes = [
            nodes_by_id[node_id]
            for node_id in region.get("catch_body_node_ids") or []
            if node_id in nodes_by_id
        ]
        scope_parts: list[str] = []
        scope_anchors: list[str] = []
        for protected_node in protected_nodes:
            summary, anchors = _exception_scope_summary(
                protected_node,
                nodes_by_as,
            )
            if summary not in scope_parts:
                scope_parts.append(summary)
            scope_anchors.extend(value for value in anchors if value)
        outcome, outcome_anchors = _exception_catch_outcome(catch_nodes)
        _add(
            ledger,
            "exception_rules",
            description=(
                f"If an exception occurs while {_joined_scope(scope_parts)}, "
                f"{outcome}. This handling applies only to those protected "
                "operations."
            ),
            evidence=[
                f"workflow_A.exception_regions.{region_index}",
                *[
                    f"workflow_A.nodes.{node['node_id']}.configured_arguments"
                    for node in catch_nodes
                ],
            ],
            anchors=[
                ["exception", "processing fails", "error occurs"],
                list(dict.fromkeys(scope_anchors))[:12],
                list(dict.fromkeys(outcome_anchors)),
                ["only while", "only during", "protected operations"],
            ],
        )

    # Explicitly record that send_reply is not recipe-terminal, preventing the
    # terminal semantics of return_response from being generalized.
    if any(
        node.get("recipe_action") == "workato_service.send_reply"
        for node in nodes
    ):
        _add(
            ledger,
            "terminal_rules",
            description=(
                "workato_service.send_reply is not inherently terminal; only "
                "an explicit stop, an inherently terminal action, or exhausted "
                "control flow ends its path."
            ),
            evidence=["workflow_A.simulator_semantics.workato_service.send_reply"],
            anchors=[["send reply"], ["not terminal"]],
            visibility="implementation_only",
            required_in_q=False,
        )

    resolution = (
        workflow_a.get("simulator_semantics", {})
        .get("reply_value_resolution", {})
    )
    for success_reply in (
        node
        for node in nodes
        if node.get("recipe_action") == "workato_service.send_reply"
        and str(
            (node.get("configured_arguments") or {}).get("reply_type") or ""
        )
        == "success"
    ):
        empty_values = _conditionally_unavailable_reply_fields(
            success_reply, nodes_by_as
        )
        conditions = _branch_local_reply_conditions(
            success_reply, nodes_by_as, nodes_by_id
        )
        if not empty_values or not conditions:
            continue
        if (
            any(value is None for value in empty_values.values())
            and resolution.get("missing_scalar_datapill_in_object") is not None
        ):
            continue
        if (
            any(value == [] for value in empty_values.values())
            and resolution.get("missing_source_mapped_array") != []
        ):
            continue
        assignments = ", ".join(
            f"{field}={'null' if value is None else '[]'}"
            for field, value in empty_values.items()
        )
        condition_text = " or ".join(
            description for _, description in conditions
        )
        _add(
            ledger,
            "required_outputs",
            description=(
                f"When the branch condition is false ({condition_text}), "
                f"return success with {assignments}."
            ),
            evidence=[
                *[
                    f"workflow_A.nodes.{controller_id}.condition"
                    for controller_id, _ in conditions
                ],
                f"workflow_A.nodes.{success_reply['node_id']}."
                "configured_arguments.reply",
                "workflow_A.simulator_semantics.reply_value_resolution",
            ],
            anchors=[
                *[
                    [
                        f"{field} null",
                        f"{field} is null",
                        f"{field}=[]",
                        f"{field} is an empty array",
                    ]
                    for field in empty_values
                ],
            ],
        )

    for success_reply in (
        node
        for node in nodes
        if node.get("recipe_action") == "workato_service.send_reply"
        and str(
            (node.get("configured_arguments") or {}).get("reply_type") or ""
        )
        == "success"
    ):
        null_record_values, nullable_source_ids = _null_record_reply_fields(
            success_reply, nodes_by_as
        )
        if not null_record_values:
            continue
        assignments = ", ".join(
            f"{field}=null" for field in null_record_values
        )
        _add(
            ledger,
            "required_outputs",
            description=(
                "When the single-record lookup succeeds but finds no "
                f"matching record, return success with {assignments}."
            ),
            evidence=[
                *[
                    f"workflow_A.nodes.{source_id}.configured_arguments"
                    for source_id in nullable_source_ids
                ],
                f"workflow_A.nodes.{success_reply['node_id']}."
                "configured_arguments.reply",
                "workflow_A.simulator_semantics.reply_value_resolution",
            ],
            anchors=[
                ["no matching record", "record is absent", "record is null"],
                ["return success", "success reply"],
                *[
                    [f"{field}=null", f"{field} is null"]
                    for field in null_record_values
                ],
            ],
        )

    total = sum(len(ledger[key]) for key in LEDGER_CATEGORIES)
    schema_label_overrides = _schema_filter_label_overrides(workflow_a)
    repeat_marker_abstracted = any(
        "the event's repeat marker" in str(item.get("description") or "")
        for category in LEDGER_CATEGORIES
        for item in ledger[category]
    )
    custom_sql_alter_effect = any(
        (effect := _custom_sql_effect(node)) is not None
        and effect[0] == "alter_table_add"
        for node in workflow_a.get("nodes") or []
        if isinstance(node, dict) and not node.get("skip")
    )
    custom_sql_extended_effect = any(
        (effect := _custom_sql_effect(node)) is not None
        and effect[0]
        in {
            "alter_external_table_refresh",
            "alter_task_resume",
            "copy_into",
            "create_task",
            "drop_table",
            "grant_select",
        }
        for node in workflow_a.get("nodes") or []
        if isinstance(node, dict) and not node.get("skip")
    )
    qualified_slack_lifecycle_label = any(
        str(node.get("benchmark_tool") or "")
        in {"slack.post_message", "slack.post_reply"}
        and re.search(
            r"\b(?:Internal|External|Original)\s+"
            r"(?:Recipe|Job)\s+(?:ID|URL|name)\b",
            json.dumps(
                node.get("configured_arguments") or {},
                ensure_ascii=False,
            ),
            flags=re.I,
        )
        for node in workflow_a.get("nodes") or []
        if isinstance(node, dict) and not node.get("skip")
    )
    extractor_versions = [LEDGER_EXTRACTOR_VERSION]
    if schema_label_overrides:
        extractor_versions.append(UUID_SCHEMA_LABEL_RESOLUTION_VERSION)
    if repeat_marker_abstracted:
        extractor_versions.append(REPEAT_MARKER_ABSTRACTION_VERSION)
    if custom_sql_alter_effect:
        extractor_versions.append(CUSTOM_SQL_ALTER_EFFECT_VERSION)
    if custom_sql_extended_effect:
        extractor_versions.append(CUSTOM_SQL_EXTENDED_EFFECT_VERSION)
    if qualified_slack_lifecycle_label:
        extractor_versions.append(
            SLACK_QUALIFIED_LIFECYCLE_LABEL_VERSION
        )
    extractor_version = "+".join(extractor_versions)
    return {
        **ledger,
        "metadata": {
            "source": "workflow_A_only",
            "extractor_version": extractor_version,
            "item_count": total,
            "workflow_A_hash": workflow_a.get("workflow_A_hash"),
            **(
                {
                    "schema_filter_label_resolution": {
                        "version": UUID_SCHEMA_LABEL_RESOLUTION_VERSION,
                        "overrides": schema_label_overrides,
                    }
                }
                if schema_label_overrides
                else {}
            ),
            **(
                {
                    "repeat_marker_abstraction": {
                        "version": REPEAT_MARKER_ABSTRACTION_VERSION,
                    }
                }
                if repeat_marker_abstracted
                else {}
            ),
            **(
                {
                    "custom_sql_alter_effect": {
                        "version": CUSTOM_SQL_ALTER_EFFECT_VERSION,
                    }
                }
                if custom_sql_alter_effect
                else {}
            ),
            **(
                {
                    "custom_sql_extended_effect": {
                        "version": CUSTOM_SQL_EXTENDED_EFFECT_VERSION,
                    }
                }
                if custom_sql_extended_effect
                else {}
            ),
            **(
                {"reachability_filter": "control-flow-effects-v2"}
                if ignored_unreachable_node_ids
                else {}
            ),
            **(
                {
                    "ignored_unreachable_action_node_ids": (
                        ignored_unreachable_action_node_ids
                    ),
                }
                if ignored_unreachable_action_node_ids
                else {}
            ),
            **(
                {
                    "ignored_unreachable_terminal_node_ids": (
                        ignored_unreachable_terminal_node_ids
                    ),
                }
                if ignored_unreachable_terminal_node_ids
                else {}
            ),
            **(
                {"ignored_skipped_node_ids": ignored_skipped_node_ids}
                if ignored_skipped_node_ids
                else {}
            ),
        },
    }


def ledger_items(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    """Return every ledger fact in stable category/insertion order."""
    return [
        item
        for category in LEDGER_CATEGORIES
        for item in ledger.get(category) or []
        if isinstance(item, dict) and item.get("ledger_id")
    ]


def required_ledger_ids(ledger: dict[str, Any]) -> list[str]:
    """Return the A-derived facts that must be represented in Q."""
    return [
        str(item["ledger_id"])
        for item in ledger_items(ledger)
        if item.get("required_in_q")
    ]


def clause_map_coverage(
    ledger: dict[str, Any],
    clause_map: list[dict[str, Any]],
) -> dict[str, Any]:
    """Check structural completeness using declared ledger IDs only.

    This checker deliberately does not infer meaning from keywords in Q. It
    verifies that generated clauses map every required A-derived ledger ID.
    The independent model critic is responsible for deciding whether each
    clause really expresses the ledger fact it claims to cover.
    """
    items = ledger_items(ledger)
    item_by_id = {
        str(item["ledger_id"]): item
        for item in items
    }
    clauses_by_ledger_id: dict[str, list[str]] = {}
    unknown_ids: set[str] = set()
    duplicate_clause_ids: set[str] = set()
    seen_clause_ids: set[str] = set()
    normalized_clauses: list[dict[str, Any]] = []
    for index, clause in enumerate(clause_map or []):
        if not isinstance(clause, dict):
            continue
        clause_id = str(clause.get("clause_id") or f"clause_{index + 1}")
        if clause_id in seen_clause_ids:
            duplicate_clause_ids.add(clause_id)
        seen_clause_ids.add(clause_id)
        covers = [
            str(value)
            for value in clause.get("covers") or []
            if str(value)
        ]
        normalized_clauses.append(
            {
                "clause_id": clause_id,
                "text": str(clause.get("text") or ""),
                "covers": covers,
            }
        )
        for ledger_id in covers:
            if ledger_id not in item_by_id:
                unknown_ids.add(ledger_id)
                continue
            clauses_by_ledger_id.setdefault(ledger_id, []).append(clause_id)

    mappings: list[dict[str, Any]] = []
    for item in items:
        ledger_id = str(item["ledger_id"])
        clause_ids = clauses_by_ledger_id.get(ledger_id, [])
        visibility = str(item.get("visibility") or "user_visible")
        if clause_ids:
            mapped_to = ["Q"]
        elif visibility == "implementation_only":
            mapped_to = ["implementation_only"]
        elif visibility == "plan_visible" and not item.get("required_in_q"):
            mapped_to = ["P"]
        else:
            mapped_to = []
        mappings.append(
            {
                "ledger_id": ledger_id,
                "description": item.get("description"),
                "required_in_q": bool(item.get("required_in_q")),
                "visibility": visibility,
                "mapped_to": mapped_to,
                "q_clause_ids": clause_ids,
                "covered": bool(mapped_to),
                "q_covered": bool(clause_ids),
            }
        )

    required_ids = required_ledger_ids(ledger)
    mapped_required_ids = [
        ledger_id
        for ledger_id in required_ids
        if clauses_by_ledger_id.get(ledger_id)
    ]
    missing_required_ids = [
        ledger_id
        for ledger_id in required_ids
        if ledger_id not in mapped_required_ids
    ]
    mapped_ids = sorted(clauses_by_ledger_id)
    return {
        "coverage_method": "declared_ledger_id_clause_map",
        "clauses": normalized_clauses,
        "mappings": mappings,
        "known_ledger_ids": list(item_by_id),
        "required_ledger_ids": required_ids,
        "mapped_ledger_ids": mapped_ids,
        "mapped_required_ledger_ids": mapped_required_ids,
        "unknown_ledger_ids": sorted(unknown_ids),
        "duplicate_clause_ids": sorted(duplicate_clause_ids),
        "ledger_coverage": (
            1.0
            if not mappings
            else sum(item["covered"] for item in mappings) / len(mappings)
        ),
        "required_ledger_coverage": (
            1.0
            if not required_ids
            else len(mapped_required_ids) / len(required_ids)
        ),
        # Compatibility aliases retained in artifacts while downstream
        # consumers migrate to the explicit required-ledger terminology.
        "required_q_coverage": (
            1.0
            if not required_ids
            else len(mapped_required_ids) / len(required_ids)
        ),
        "unmapped_ledger_items": [
            item["ledger_id"] for item in mappings if not item["covered"]
        ],
        "missing_required_ledger_ids": missing_required_ids,
        "missing_required_q_items": missing_required_ids,
    }
