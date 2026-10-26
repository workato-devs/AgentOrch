"""Read the benchmark's public tool catalog without constructing clients."""

from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path
from typing import Any


ACTION_ALIASES = {
    "slack_bot.post_bot_reply_v2": "slack.post_reply",
    "slack_bot.post_bot_message": "slack.post_message",
    "slack.post_message_to_channel": "slack.post_message",
    "slack.get_user_by_email": "slack_bot.get_user_by_email",
    "slack_bot.update_blocks_by_block_id": "slack.update_blocks_by_block_id",
    "salesforce.search_sobjects_soql_bulk_csv_v2": "salesforce.search_records",
    "salesforce.search_sobjects_soql_v2": "salesforce.search_records",
    "salesforce.search_sobjects_soql": "salesforce.search_records",
    "salesforce.search_sobjects": "salesforce.search_records",
    "salesforce.get_custom_object": "salesforce.search_records",
    "salesforce.update_sobject": "salesforce.update_record",
    "salesforce.composite_update_sobject": "salesforce.update_record",
    "salesforce.upsert_sobject": "salesforce.upsert_record",
    "salesforce.create_custom_object": "salesforce.create_record",
    "salesforce.create_sobject": "salesforce.create_record",
    "json_parser.parse_json": "workato_runtime.parse_json",
    "workato_variable.declare_variable": "workato_runtime.declare_variable",
    "workato_variable.declare_list": "workato_runtime.declare_list",
    "workato_variable.update_variables": "workato_runtime.update_variables",
    "workato_variable.update_variable": "workato_runtime.update_variable",
    "workato_variable.insert_to_list": "workato_runtime.insert_to_list",
    "workato_variable.insert_to_list_batch": (
        "workato_runtime.insert_to_list_batch"
    ),
    "workato_list.create_list": "workato_runtime.create_list",
    "workato_list.accumulate_list_items": (
        "workato_runtime.accumulate_list_items"
    ),
    "logger.log_message": "workato_runtime.log_message",
    "google_sheets.add_row_v4_bulk": (
        "google_sheets.add_spreadsheet_row_v4"
    ),
}

RUNTIME_INTERNAL_ACTIONS = {
    "json_parser.parse_json",
    "workato_smart_list.create_list_from_csv",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "workato_variable.declare_variable",
    "workato_variable.declare_list",
    "workato_variable.update_variables",
    "workato_variable.update_variable",
    "workato_variable.insert_to_list",
    "workato_variable.insert_to_list_batch",
    "workato_list.create_list",
    "workato_list.accumulate_list_items",
    "logger.log_message",
    "google_sheets.add_row_v4_bulk",
}


class ToolCatalog:
    def __init__(
        self,
        specs: list[dict[str, Any]],
        source: str,
    ) -> None:
        self.source = source
        self.specs = {
            str(spec["name"]): spec
            for spec in specs
            if isinstance(spec, dict) and spec.get("name")
        }

    @classmethod
    def from_benchmark(
        cls,
        project_root: Path,
        source: str = "simulated",
    ) -> "ToolCatalog":
        if source not in {"simulated", "real"}:
            raise ValueError("registry source must be 'simulated' or 'real'")
        source_root = project_root / "benchmark" / source / "src"
        if not source_root.is_dir():
            raise RuntimeError(
                f"benchmark registry source is missing: {source_root}"
            )
        module_path = (
            source_root
            / "benchmark"
            / (
                "simulated_tools.py"
                if source == "simulated"
                else "live_tools.py"
            )
        )
        specs = _read_literal_registry_specs(module_path)
        _merge_authoritative_contracts(
            specs,
            (
                project_root
                / "task_description"
                / "config"
                / "simulator_tool_specs.json"
                if source == "simulated"
                else None
            ),
        )
        return cls(specs, source)

    def canonical_tool(
        self,
        raw_tool: str,
        node: dict[str, Any] | None = None,
    ) -> str:
        return ACTION_ALIASES.get(raw_tool, raw_tool)

    def status(
        self,
        raw_tool: str,
        node: dict[str, Any] | None = None,
    ) -> str:
        canonical = self.canonical_tool(raw_tool, node)
        if raw_tool in RUNTIME_INTERNAL_ACTIONS:
            return "runtime_internal"
        if canonical in self.specs:
            return "registered"
        return "unregistered"

    def spec_for(
        self,
        raw_tool: str,
        node: dict[str, Any],
    ) -> dict[str, Any] | None:
        canonical = self.canonical_tool(raw_tool, node)
        if raw_tool in RUNTIME_INTERNAL_ACTIONS:
            return {
                "name": canonical,
                "description": f"Recipe-local Workato operation: {raw_tool}.",
                "input_schema": workato_schema_to_json_schema(
                    node.get("extended_input_schema") or []
                ),
                "scope": "runtime_internal",
            }
        if canonical in self.specs:
            return dict(self.specs[canonical])
        return None

    def is_external(self, tool: str) -> bool:
        return tool in self.specs


def _read_literal_registry_specs(path: Path) -> list[dict[str, Any]]:
    """Read tool contracts without constructing live or simulated clients."""

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except FileNotFoundError as exc:
        raise RuntimeError(f"tool registry module is missing: {path}") from exc
    specs: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if (
            not isinstance(node, ast.Call)
            or not isinstance(node.func, ast.Attribute)
            or node.func.attr != "register"
            or not node.args
        ):
            continue
        try:
            name = ast.literal_eval(node.args[0])
        except (ValueError, TypeError):
            continue
        keywords = {
            keyword.arg: keyword.value
            for keyword in node.keywords
            if keyword.arg is not None
        }
        try:
            exposed = (
                ast.literal_eval(keywords["expose_to_agent"])
                if "expose_to_agent" in keywords
                else True
            )
            description = ast.literal_eval(keywords["description"])
            input_schema = ast.literal_eval(keywords["input_schema"])
        except (KeyError, ValueError, TypeError) as exc:
            raise RuntimeError(
                f"tool {name!r} in {path} does not use a literal public schema"
            ) from exc
        if exposed:
            specs.append(
                {
                    "name": str(name),
                    "description": str(description),
                    "input_schema": input_schema,
                }
            )
    if not specs:
        raise RuntimeError(f"no public tool registrations found in {path}")
    return specs


_ERROR_OBSERVATION_SCHEMA = {
    "type": "string",
    "pattern": r"^ERROR:",
    "description": (
        "A failed call is returned to the model as a text observation prefixed "
        "with 'ERROR:'; it is not a successful tool result."
    ),
}

_GENERIC_SUCCESS_SCHEMA = {
    "type": "object",
    "additionalProperties": True,
    "description": (
        "A successful call returns a JSON object. Tool-specific fields are "
        "documented when the adapter has a stable, narrower result contract."
    ),
}

_CANONICAL_OUTPUT_OVERRIDES: dict[str, dict[str, Any]] = {
    "workato_db_table.get_records": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "records": {"type": "array", "items": {"type": "object"}},
            "continuation_token": {"type": ["string", "number", "null"]},
        },
        "required": ["ok", "records"],
    },
    "slack.post_message": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "channel": {"type": "string"},
            "ts": {"type": "string"},
            "thread_ts": {"type": "string"},
            "message": {"type": "object"},
        },
        "required": ["ok"],
    },
    "snowflake.run_custom_sql": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "rows": {"type": "array", "items": {"type": "object"}},
            "row_count": {"type": "integer"},
            "rows_affected": {"type": "integer"},
        },
        "required": ["ok", "rows", "rows_affected"],
    },
    "workato_app.start_recipe": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "recipe_id": {"type": "string"},
        },
        "required": ["ok", "recipe_id"],
    },
    "workato_app.stop_recipe": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "recipe_id": {"type": "string"},
        },
        "required": ["ok", "recipe_id"],
    },
    "workato_api_platform.return_response": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "http_status_code": {"type": "string"},
            "response": {},
            "response_headers": {
                "type": "object",
                "additionalProperties": {"type": "string"},
            },
        },
        "required": ["ok", "http_status_code"],
    },
}


def _canonical_argument_rules(name: str) -> dict[str, Any]:
    """Return recipe-independent rules for the one scored argument form.

    Tool input schemas describe what the adapter can receive.  They are not,
    by themselves, a canonicalization policy: a permissive schema may accept
    several spellings even though exact-trace scoring has exactly one public
    representation.  These rules document the deterministic projection used
    by both ``canonical_tool_arguments`` and ``RawWorkatoRuntime``.  They are
    generated solely from the canonical tool name and therefore cannot leak a
    recipe's selected tool, fields, constants, or node order.
    """

    rules: dict[str, Any] = {
        "schema_version": "agentorch-canonical-argument-rules-v1",
        "comparison": "exact_canonical_arguments",
        "object_key_order": "canonical_json_sorted_keys",
        "semantic_rewrites": "forbidden",
        "query_normalization": (
            "For query/sql/where/order arguments, exact scoring discards "
            "insignificant whitespace, line endings, one trailing semicolon, "
            "and SQL/SOQL keyword case. Quoted literals/identifiers, comments, "
            "token order, projections, sources, joins, predicates, grouping, "
            "ordering, limits, and bindings remain exact."
        ),
        "scalar_types": (
            "Use the JSON type declared by the canonical input schema. Do not "
            "interchange strings, numbers, booleans, or null unless a "
            "tool-specific normalization below explicitly requires it."
        ),
        "caught_error_binding": (
            "A caught error's message field is the underlying exception text "
            "without the interactive tool-observation 'ERROR:' transport "
            "prefix. Preserve that message exactly in any downstream field "
            "bound to it."
        ),
    }
    if name == "salesforce.search_records":
        rules.update(
            {
                "comparison": "exact_non_query_arguments_plus_query_semantics",
                "semantic_rewrites": "query_surface_only",
                "query_comparison": "runtime_result_or_state_equivalence",
                "query_normalization": (
                    "No syntax normalization defines correctness; execute the "
                    "connector and compare the selected row multiset."
                ),
                "argument_shape": {
                    "always": ["sobject", "query"],
                    "optional": ["filters", "limit"],
                },
                "selection_mode": (
                    "SOQL text, equality filters, and a separate limit are one "
                    "query surface. Alternative encodings are accepted only "
                    "when the executed connector returns the same row multiset."
                ),
                "query_encoding": (
                    "SOQL spelling and structure are not compared directly. The "
                    "Salesforce object stays exact and the executed selection "
                    "must return the same business records on every variant."
                ),
                "limit_encoding": (
                    "Limit placement is part of query semantics. If supplied as "
                    "a connector field, its transport type is a non-negative "
                    "JSON integer. Do not encode it as a numeric string."
                ),
                "boolean_encoding": (
                    "Equality-filter values use JSON booleans for boolean "
                    "fields. Boolean tokens inside query remain query syntax."
                ),
            }
        )
    elif name == "slack.post_reply":
        rules.update(
            {
                "invoking_context_encoding": (
                    "The invoking channel, thread timestamp, user, and original "
                    "timestamp are connector-injected transport context and are "
                    "omitted from the canonical request. Omit false optional "
                    "mode flags; include ephemeral, replace_original, or "
                    "delete_original only when true. Destination correctness is "
                    "still checked from the resulting Slack side effect."
                )
            }
        )
    elif name == "salesforce.update_record":
        rules.update(
            {
                "argument_shape": {
                    "scalar": ["sobject", "id", "fields"],
                    "batch": ["sobject", "records"],
                },
                "batch_encoding": (
                    "A scalar record update uses exactly {sobject, id, fields}. "
                    "An imported composite/batch update uses exactly {sobject, "
                    "records}, where every records item is {sobject, id, fields}. "
                    "Batch form is retained even when runtime expansion yields "
                    "one item; cardinality never changes the argument shape."
                ),
                "field_encoding": (
                    "fields contains only mapped Salesforce fields. Connector "
                    "authoring metadata is omitted, and an absent optional value "
                    "is omitted rather than encoded as null."
                ),
            }
        )
    elif name == "workato_db_table.get_records":
        rules.update(
            {
                "argument_shape": {
                    "always": ["table_id", "filters"],
                    "optional": [
                        "continuation_token",
                        "limit",
                        "order_by_field_id",
                        "order_direction",
                    ],
                },
                "filter_encoding": (
                    "Each filter is exactly {field_id, op, value}. Replace '-' "
                    "with '_' in field_id. Lowercase op and canonicalize "
                    "equals to eq. Encode istrue/isfalse as op='eq' with JSON "
                    "boolean true/false. Preserve an explicitly "
                    "configured value for isnull/isnotnull; use null only when "
                    "no value was configured."
                ),
                "modifier_encoding": (
                    "Omit editor defaults limit=100 and order_direction='asc' "
                    "when order_by_field_id is absent. Retain a non-default "
                    "limit as a JSON integer. When order_by_field_id is present, "
                    "replace '-' with '_', include order_direction (default "
                    "'asc'), and retain an explicitly configured limit."
                ),
            }
        )
    elif name == "snowflake.search_rows":
        rules.update(
            {
                "argument_shape": {
                    "always": [
                        "table",
                        "where",
                        "parameters",
                        "limit",
                        "offset",
                        "orderby",
                        "output_columns",
                    ]
                },
                "parameter_encoding": (
                    "parameters is exactly the configured parameters.data "
                    "object, or {} when absent."
                ),
                "pagination_encoding": (
                    "limit and offset are JSON integers when present and null "
                    "when absent. Numeric strings are not canonical."
                ),
                "query_encoding": (
                    "where, orderby, and output_columns remain separate fields; "
                    "do not replace this structured call with SQL text."
                ),
            }
        )
    elif name == "snowflake.search_rows_sql":
        rules.update(
            {
                "comparison": "exact_non_query_arguments_plus_query_semantics",
                "semantic_rewrites": "query_surface_only",
                "query_comparison": "runtime_result_or_state_equivalence",
                "query_normalization": (
                    "No syntax normalization defines correctness; execute the "
                    "connector and compare the selected row multiset."
                ),
                "argument_shape": {
                    "always": ["sql", "parameters", "limit", "offset"]
                },
                "parameter_encoding": (
                    "parameters is exactly the configured parameters.data "
                    "object, or {} when absent."
                ),
                "pagination_encoding": (
                    "limit and offset are JSON integers when present and null "
                    "when absent. Numeric strings are not canonical."
                ),
                "query_encoding": (
                    "SQL spelling and structure are not compared directly. The "
                    "executed read must return the same row multiset on every "
                    "variant; parameters and pagination participate in that "
                    "query result semantics."
                ),
            }
        )
    elif name == "snowflake.run_custom_sql":
        rules.update(
            {
                "comparison": "exact_non_query_arguments_plus_query_semantics",
                "semantic_rewrites": "query_surface_only",
                "query_comparison": "runtime_result_or_state_equivalence",
                "query_normalization": (
                    "No syntax normalization defines correctness; execute reads "
                    "and compare row multisets, or execute writes and compare "
                    "the final Snowflake table state."
                ),
                "argument_shape": {"always": ["sql", "parameters"]},
                "parameter_encoding": (
                    "parameters is exactly the configured parameters.data "
                    "object, or {} when absent."
                ),
                "query_encoding": (
                    "SQL spelling and structure are not compared directly. Reads "
                    "must return the same row multiset; mutating statements "
                    "must leave the same Snowflake table state on every variant."
                ),
            }
        )
    elif name == "workato_api_platform.return_response":
        rules.update(
            {
                "argument_shape": {
                    "always": ["http_status_code", "response"],
                    "optional": ["response_headers"],
                },
                "status_encoding": (
                    "http_status_code is a JSON string; use '200' only when the "
                    "recipe declares no other status."
                ),
            }
        )
    elif name == "google_sheets.search_spreadsheet_rows_v4_new":
        rules.update(
            {
                "argument_shape": {
                    "always": ["spreadsheet", "sheet", "data", "count"]
                },
                "count_encoding": (
                    "count is a non-negative JSON integer when present and null "
                    "when absent. Numeric strings are not canonical."
                ),
                "filter_encoding": (
                    "data is the exact object of column-name equality filters; "
                    "do not move a filter into a query string."
                ),
            }
        )
    elif name == "google_drive.create_folder":
        rules.update(
            {
                "argument_shape": {"always": ["parent_id", "name"]},
                "parent_encoding": (
                    "Use parent_id only. folderId is connector-authoring input "
                    "and is not a canonical benchmark argument alias."
                ),
            }
        )
    elif name == "jira.create_issue":
        rules.update(
            {
                "argument_shape": {
                    "always": [
                        "project_issuetype",
                        "summary",
                        "description",
                        "priority",
                        "labels",
                    ]
                },
                "optional_value_encoding": (
                    "All five canonical keys are present. Unconfigured optional "
                    "text fields are empty strings and unconfigured labels is null."
                ),
            }
        )
    elif name == "workato_db_table.upsert_record":
        rules.update(
            {
                "argument_shape": {
                    "always": ["table_id", "primary_field_id", "record"]
                },
                "identity_encoding": (
                    "Use primary_field_id only. record_id and record_id_field "
                    "are not aliases in the canonical upsert call."
                ),
                "field_encoding": (
                    "Replace '-' with '_' in primary_field_id and record keys."
                ),
            }
        )
    elif name == "workato_runtime.create_list":
        rules.update(
            {
                "argument_shape": {"always": ["name", "size"]},
                "size_encoding": (
                    "size is one non-negative JSON integer. Numeric strings are "
                    "not canonical; when the recipe creates a list from a source, "
                    "size is the resolved source length."
                ),
            }
        )
    return rules


def _side_effect_contract(name: str) -> dict[str, Any]:
    operation = name.rsplit(".", 1)[-1].lower()
    read_prefixes = (
        "find",
        "get",
        "list",
        "lookup",
        "read",
        "search",
    )
    terminal = name == "workato_api_platform.return_response"
    communication = name.startswith("slack.") and operation in {
        "post_message",
        "post_reply",
    }
    lifecycle = name.startswith("workato_app.") and operation in {
        "rerun_jobs",
        "start_recipe",
        "stop_recipe",
    }
    recipe_local = name.startswith(("workato_runtime.", "workato_smart_list."))
    read_only = operation.startswith(read_prefixes)
    if terminal:
        effect_class = "terminal_response"
    elif communication:
        effect_class = "communication"
    elif lifecycle:
        effect_class = "lifecycle_transition"
    elif recipe_local:
        effect_class = "recipe_local_state"
    elif read_only:
        effect_class = "read"
    else:
        effect_class = "external_write"
    return {
        "class": effect_class,
        "mutates_external_state": effect_class
        in {"communication", "external_write", "lifecycle_transition"},
        "terminal_on_success": terminal,
    }


def _merge_authoritative_contracts(
    specs: list[dict[str, Any]],
    path: Path | None,
) -> None:
    """Add public adapter contracts without consulting a recipe or variant.

    The runtime registry is authoritative for names and accepted inputs.  The
    checked-in adapter catalog additionally documents outputs and stable
    behavior that cannot be recovered from ``ToolRegistry.register`` (whose
    dataclass stores only input_schema).  Merging by canonical benchmark tool
    keeps every recipe in a connector family on the identical tool surface;
    consequently this enrichment cannot reveal which tool the gold workflow
    selected.
    """

    if path is None:
        raw: Any = {}
    else:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"authoritative simulator tool contracts are missing: {path}"
            ) from exc
    if not isinstance(raw, dict):
        raise RuntimeError(f"simulator tool contracts must be an object: {path}")

    by_canonical: dict[str, list[dict[str, Any]]] = {}
    for item in raw.values():
        if not isinstance(item, dict):
            continue
        canonical = str(item.get("benchmark_tool") or "").strip()
        if canonical:
            by_canonical.setdefault(canonical, []).append(item)

    for spec in specs:
        canonical = str(spec.get("name") or "")
        contracts = by_canonical.get(canonical, [])
        output_schemas = [
            item["output_schema"]
            for item in contracts
            if isinstance(item.get("output_schema"), dict)
        ]
        if output_schemas:
            first = output_schemas[0]
            if any(candidate != first for candidate in output_schemas[1:]):
                raise RuntimeError(
                    "conflicting output schemas for canonical tool "
                    f"{canonical!r} in {path}"
                )
            spec["output_schema"] = deepcopy(first)
        elif canonical in _CANONICAL_OUTPUT_OVERRIDES:
            spec["output_schema"] = deepcopy(
                _CANONICAL_OUTPUT_OVERRIDES[canonical]
            )
        else:
            # ToolRegistry.call rejects non-object success values, so this is
            # an authoritative minimum contract rather than a guessed shape.
            spec["output_schema"] = deepcopy(_GENERIC_SUCCESS_SCHEMA)

        notes = sorted(
            {
                str(note).strip()
                for item in contracts
                for note in (item.get("behavior_notes") or [])
                if str(note).strip()
            }
        )
        spec["error_schema"] = deepcopy(_ERROR_OBSERVATION_SCHEMA)
        semantic_constraints: dict[str, Any] = {
            "error_delivery": "error_observation",
        }
        for item in contracts:
            configured_constraints = item.get("semantic_constraints") or {}
            if not isinstance(configured_constraints, dict):
                raise RuntimeError(
                    "semantic_constraints must be an object for canonical tool "
                    f"{canonical!r} in {path}"
                )
            for key, value in configured_constraints.items():
                if key in semantic_constraints and semantic_constraints[key] != value:
                    raise RuntimeError(
                        "conflicting semantic constraint "
                        f"{key!r} for canonical tool {canonical!r} in {path}"
                    )
                semantic_constraints[key] = deepcopy(value)
        if canonical == "workato_db_table.get_records":
            semantic_constraints["filter_operator_semantics"] = {
                "eq": "Field value equals the supplied value.",
                "ne": "Field value does not equal the supplied value.",
                "gte": "Field value is greater than or equal to the supplied value.",
                "gt": "Field value is greater than the supplied value.",
                "lte": "Field value is less than or equal to the supplied value.",
                "lt": "Field value is less than the supplied value.",
                "starts_with": "Field text starts with the supplied value.",
                "isnull": (
                    "Field is null or empty. Any supplied value is retained in "
                    "the call but ignored by this presence test."
                ),
                "isnotnull": (
                    "Field is neither null nor empty. Any supplied value is "
                    "retained in the call but ignored by this presence test."
                ),
            }
        if canonical in {
            "snowflake.run_custom_sql",
            "snowflake.search_rows",
            "snowflake.search_rows_sql",
        }:
            # Encoding is exact-canonical and lives in canonical_argument_rules.
            # semantic_constraints is reserved for connector behavior, never a
            # primary-scoring equivalence class.
            pass
        if notes:
            semantic_constraints["behavior_notes"] = notes
        spec["semantic_constraints"] = semantic_constraints
        spec["canonical_argument_rules"] = _canonical_argument_rules(canonical)
        spec["side_effects"] = _side_effect_contract(canonical)


def workato_schema_to_json_schema(value: Any) -> dict[str, Any]:
    fields = value if isinstance(value, list) else []
    properties: dict[str, Any] = {}
    required: list[str] = []
    for field in fields:
        if not isinstance(field, dict) or not field.get("name"):
            continue
        name = str(field["name"])
        properties[name] = _workato_field_schema(field)
        if field.get("optional") is False:
            required.append(name)
    result: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        result["required"] = required
    return result


def _workato_field_schema(field: dict[str, Any]) -> dict[str, Any]:
    raw_type = str(field.get("type") or "string")
    type_map = {
        "integer": "integer",
        "number": "number",
        "float": "number",
        "boolean": "boolean",
        "object": "object",
        "array": "array",
        "date": "string",
        "date_time": "string",
    }
    schema: dict[str, Any] = {"type": type_map.get(raw_type, "string")}
    if field.get("label"):
        schema["title"] = str(field["label"])
    if raw_type in {"date", "date_time"}:
        schema["format"] = "date-time" if raw_type == "date_time" else "date"
    children = field.get("properties")
    if isinstance(children, list):
        schema.update(workato_schema_to_json_schema(children))
    if raw_type == "array":
        item = field.get("of") or field.get("items")
        if isinstance(item, dict):
            schema["items"] = _workato_field_schema(item)
        elif isinstance(children, list):
            schema["items"] = workato_schema_to_json_schema(children)
        else:
            schema["items"] = {}
    return schema
