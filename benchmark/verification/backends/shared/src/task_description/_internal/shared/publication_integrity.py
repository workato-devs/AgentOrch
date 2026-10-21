"""Deterministic integrity checks for public task-description packages.

This module intentionally contains no model calls and no evaluation-policy
logic.  It validates only the construction-time boundary between the private
recipe artifacts and the public package/instances emitted by Stage 7.
"""

from __future__ import annotations

import json
import re
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from .pipeline_common import file_sha256, stable_json_hash


CANONICAL_JSON_SPEC = (
    "UTF-8 JSON; object keys sorted lexicographically; compact separators; "
    "Unicode preserved; NaN and infinities forbidden"
)


def _without_hash(value: dict[str, Any], field: str) -> dict[str, Any]:
    payload = deepcopy(value)
    payload.pop(field, None)
    return payload


def declared_hash_matches(value: dict[str, Any], field: str) -> bool:
    """Return whether ``field`` hashes the canonical object without itself."""

    declared = value.get(field)
    return isinstance(declared, str) and declared == stable_json_hash(
        _without_hash(value, field)
    )


def _git_output(project_root: Path, *arguments: str) -> str | None:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def pipeline_provenance(
    project_root: Path,
    *,
    source_paths: Iterable[Path],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Bind a publication to code bytes as well as the ambient git commit.

    A commit alone is insufficient in a dirty worktree.  The source digest is
    therefore computed over the exact generator modules/configuration named by
    the caller, while the git fields remain useful human-facing lineage.
    """

    relative_sources: dict[str, str] = {}
    normalized_paths: list[Path] = []
    for source in sorted({Path(path).resolve() for path in source_paths}):
        if not source.is_file():
            raise ValueError(f"pipeline provenance source does not exist: {source}")
        try:
            relative = source.relative_to(project_root.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError(
                f"pipeline provenance source is outside project root: {source}"
            ) from exc
        relative_sources[relative] = file_sha256(source)
        normalized_paths.append(Path(relative))

    commit = _git_output(project_root, "rev-parse", "HEAD")
    global_status = _git_output(
        project_root,
        "status",
        "--porcelain",
        "--untracked-files=normal",
    )
    relevant_status = _git_output(
        project_root,
        "status",
        "--porcelain",
        "--untracked-files=normal",
        "--",
        *(path.as_posix() for path in normalized_paths),
    )
    result = {
        "schema_version": "agentorch-generation-provenance-v1",
        "canonical_json": CANONICAL_JSON_SPEC,
        "git_commit": commit,
        "git_worktree_dirty": None if global_status is None else bool(global_status),
        "relevant_sources_dirty": (
            None if relevant_status is None else bool(relevant_status)
        ),
        "pipeline_source_files": relative_sources,
        "pipeline_source_hash": stable_json_hash(relative_sources),
        "pipeline_config": deepcopy(config),
        "pipeline_config_hash": stable_json_hash(config),
    }
    result["provenance_hash"] = stable_json_hash(result)
    return result


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _accepted_types(schema: dict[str, Any]) -> set[str]:
    declared = schema.get("type")
    if isinstance(declared, str):
        values = {declared}
    elif isinstance(declared, list):
        values = {str(item) for item in declared}
    else:
        values = set()
    if "number" in values:
        values.add("integer")
    return values


def validate_json_schema_value(
    value: Any,
    schema: dict[str, Any],
    *,
    path: str = "$",
    closed_world: bool = True,
) -> list[str]:
    """Validate the JSON-Schema subset emitted by the task pipeline.

    The construction boundary is deliberately closed-world even when an
    authoring schema omitted ``additionalProperties``.  Tool observations use
    their own schemas and are not validated by this function.
    """

    errors: list[str] = []
    accepted = _accepted_types(schema)
    actual = _json_type(value)
    if accepted and actual not in accepted:
        return [f"{path} has type {actual}, expected {sorted(accepted)}"]
    enum = schema.get("enum")
    if isinstance(enum, list) and value not in enum:
        errors.append(f"{path} is not one of the declared enum values")

    if isinstance(value, dict):
        properties = schema.get("properties")
        properties = properties if isinstance(properties, dict) else {}
        required = {
            str(item)
            for item in schema.get("required") or []
            if isinstance(item, (str, int))
        }
        missing = sorted(required - set(value))
        errors.extend(f"{path}.{name} is required" for name in missing)
        if closed_world:
            extras = sorted(set(value) - set(properties))
            errors.extend(f"{path}.{name} is not declared" for name in extras)
        for name, child in value.items():
            child_schema = properties.get(name)
            if isinstance(child_schema, dict):
                errors.extend(
                    validate_json_schema_value(
                        child,
                        child_schema,
                        path=f"{path}.{name}",
                        closed_world=closed_world,
                    )
                )
    elif isinstance(value, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, child in enumerate(value):
                errors.extend(
                    validate_json_schema_value(
                        child,
                        item_schema,
                        path=f"{path}[{index}]",
                        closed_world=closed_world,
                    )
                )
    return errors


def _empty_runtime_value(value: Any) -> bool:
    return value is None or value == "" or value == {} or value == []


def _project_to_schema(
    value: Any,
    schema: dict[str, Any],
    *,
    path: str,
) -> tuple[Any, list[dict[str, Any]], list[str]]:
    """Project private/runtime transport noise to a closed public schema."""

    dropped: list[dict[str, Any]] = []
    errors: list[str] = []
    if isinstance(value, dict):
        properties = schema.get("properties")
        properties = properties if isinstance(properties, dict) else {}
        projected: dict[str, Any] = {}
        for name, child in value.items():
            child_path = f"{path}.{name}"
            child_schema = properties.get(name)
            if not isinstance(child_schema, dict):
                dropped.append(
                    {
                        "path": child_path,
                        "reason": "undeclared_transport_field",
                        "empty": _empty_runtime_value(child),
                    }
                )
                continue
            projected_child, child_dropped, child_errors = _project_to_schema(
                child,
                child_schema,
                path=child_path,
            )
            projected[name] = projected_child
            dropped.extend(child_dropped)
            errors.extend(child_errors)
        return projected, dropped, errors
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        projected_items: list[Any] = []
        for index, child in enumerate(value):
            projected, child_dropped, child_errors = _project_to_schema(
                child,
                schema["items"],
                path=f"{path}[{index}]",
            )
            projected_items.append(projected)
            dropped.extend(child_dropped)
            errors.extend(child_errors)
        return projected_items, dropped, errors
    accepted = _accepted_types(schema)
    if isinstance(value, str) and "string" not in accepted:
        text = value.strip()
        if "boolean" in accepted and text.casefold() in {"true", "false"}:
            return text.casefold() == "true", dropped, errors
        if "integer" in accepted and re.fullmatch(r"[+-]?\d+", text):
            return int(text), dropped, errors
        if "number" in accepted:
            try:
                number = float(text)
            except ValueError:
                pass
            else:
                if number == number and number not in {
                    float("inf"),
                    float("-inf"),
                }:
                    return number, dropped, errors
    return deepcopy(value), dropped, errors


def normalize_public_runtime_input(
    runtime_payload: dict[str, Any],
    *,
    input_schema: dict[str, Any],
    execution_context_schema: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Produce and validate the model-visible per-variant runtime payload."""

    normalized: dict[str, Any] = {}
    dropped: list[dict[str, Any]] = []
    errors: list[str] = []
    for field in ("trigger_input", "runtime_input"):
        if field not in runtime_payload:
            continue
        projected, item_dropped, item_errors = _project_to_schema(
            runtime_payload[field],
            input_schema,
            path=f"$.{field}",
        )
        normalized[field] = projected
        dropped.extend(item_dropped)
        errors.extend(item_errors)
        errors.extend(
            validate_json_schema_value(
                projected,
                input_schema,
                path=f"$.{field}",
                closed_world=True,
            )
        )

    if "execution_context" in runtime_payload:
        projected, item_dropped, item_errors = _project_to_schema(
            runtime_payload["execution_context"],
            execution_context_schema,
            path="$.execution_context",
        )
        normalized["execution_context"] = projected
        dropped.extend(item_dropped)
        errors.extend(item_errors)
        errors.extend(
            validate_json_schema_value(
                projected,
                execution_context_schema,
                path="$.execution_context",
                closed_world=True,
            )
        )

    for field in sorted(set(runtime_payload) - {"trigger_input", "runtime_input", "execution_context"}):
        dropped.append(
            {
                "path": f"$.{field}",
                "reason": "noncontract_runtime_metadata",
                "empty": _empty_runtime_value(runtime_payload[field]),
            }
        )

    report = {
        "schema_version": "agentorch-runtime-interface-report-v1",
        "closed_world": True,
        "passed": not errors,
        "errors": errors,
        "dropped_fields": dropped,
    }
    report["report_hash"] = stable_json_hash(report)
    return normalized, report


def _schema_at_path(schema: dict[str, Any], path: list[str]) -> dict[str, Any] | None:
    current: Any = schema
    index = 0
    while index < len(path):
        if not isinstance(current, dict):
            return None
        part = path[index]
        if current.get("type") == "array" and part in {
            "<current_item>",
            "current_item",
        }:
            current = current.get("items")
            index += 1
            continue
        properties = current.get("properties")
        if not isinstance(properties, dict):
            return None
        # Workspace/account properties are allowed to use dotted names (for
        # example ``Salesforce.base.url``).  Public bindings use dotted paths
        # too, so prefer the longest property key that matches the remaining
        # segments before treating dots as object traversal.
        matched: str | None = None
        matched_end = index
        for end in range(len(path), index, -1):
            candidate = ".".join(path[index:end])
            if candidate in properties:
                matched = candidate
                matched_end = end
                break
        if matched is None:
            return None
        current = properties[matched]
        index = matched_end
    return current if isinstance(current, dict) else None


def workflow_input_binding_report(
    workflow_plan: dict[str, Any],
    *,
    input_schema: dict[str, Any],
    execution_context_schema: dict[str, Any],
    tool_surface: list[dict[str, Any]],
) -> dict[str, Any]:
    """Check every public input binding in the private canonical plan."""

    tool_schemas = {
        str(card.get("name") or ""): card.get("input_schema") or {}
        for card in tool_surface
        if isinstance(card, dict)
    }
    rows: list[dict[str, Any]] = []
    local_state_names: set[str] = set()

    def collect_local_state(nodes: Iterable[dict[str, Any]]) -> None:
        for node in nodes:
            if not isinstance(node, dict):
                continue
            tool = str(node.get("tool") or "")
            arguments = node.get("arguments") or {}
            if tool == "workato_runtime.declare_variable":
                variables = arguments.get("variables") if isinstance(arguments, dict) else None
                expression = variables.get("expression") if isinstance(variables, dict) else None
                fields = expression.get("fields") if isinstance(expression, dict) else None
                schema_binding = fields.get("schema") if isinstance(fields, dict) else None
                schema_text = schema_binding.get("literal") if isinstance(schema_binding, dict) else None
                if isinstance(schema_text, str):
                    try:
                        declared_fields = json.loads(schema_text)
                    except json.JSONDecodeError:
                        declared_fields = []
                    local_state_names.update(
                        str(field.get("name") or "")
                        for field in declared_fields
                        if isinstance(field, dict) and field.get("name")
                    )
            if tool == "workato_runtime.update_variables" and isinstance(arguments, dict):
                local_state_names.update(
                    str(key)
                    for key in arguments
                    if key not in {"name", "variables"}
                )
            for key in ("workflow", "then", "else", "body", "catch"):
                children = node.get(key)
                if isinstance(children, list):
                    collect_local_state(children)

    collect_local_state(workflow_plan.get("workflow") or [])

    def visit_binding(
        value: Any,
        *,
        node_id: str,
        tool: str,
        argument: str,
        target_schema: dict[str, Any] | None,
        in_catch: bool,
        direct: bool,
    ) -> None:
        if isinstance(value, list):
            for child in value:
                visit_binding(
                    child,
                    node_id=node_id,
                    tool=tool,
                    argument=argument,
                    target_schema=None,
                    in_catch=in_catch,
                    direct=False,
                )
            return
        if not isinstance(value, dict):
            return
        if "input_ref" in value:
            reference = str(value.get("input_ref") or "")
            parts = [part for part in reference.split(".") if part]
            source_class = "public_input"
            error_context_compat = in_catch and reference in {
                "action",
                "adapter",
                "error",
                "error.message",
                "error_type_id",
                "line_number",
                "message",
                "retry_count",
                "type",
            }
            local_state_compat = reference in local_state_names
            if error_context_compat or local_state_compat:
                # Catch fields shadow same-named trigger fields.  In
                # particular, a public trigger can have an object named
                # ``message`` while catch.message is always error text.
                source_schema = None
            elif parts and parts[0] == "execution_context":
                source_class = "execution_context"
                source_schema = _schema_at_path(
                    execution_context_schema,
                    parts[1:],
                )
            else:
                source_schema = _schema_at_path(input_schema, parts)
            exists = source_schema is not None or error_context_compat or local_state_compat
            type_compatible = True
            if (
                exists
                and source_schema is not None
                and direct
                and isinstance(target_schema, dict)
            ):
                source_types = _accepted_types(source_schema)
                target_types = _accepted_types(target_schema)
                type_compatible = bool(
                    not source_types
                    or not target_types
                    or source_types & target_types
                )
            rows.append(
                {
                    "plan_node_ref": node_id,
                    "tool": tool,
                    "argument": argument,
                    "input_ref": reference,
                    "source_class": (
                        "caught_error_context"
                        if error_context_compat
                        else "recipe_local_state"
                        if local_state_compat
                        else source_class
                    ),
                    "path_exists": exists,
                    "type_compatible": type_compatible,
                    "passed": exists and type_compatible,
                }
            )
            return
        for child in value.values():
            visit_binding(
                child,
                node_id=node_id,
                tool=tool,
                argument=argument,
                target_schema=None,
                in_catch=in_catch,
                direct=False,
            )

    def visit_nodes(nodes: Iterable[dict[str, Any]], *, in_catch: bool = False) -> None:
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("id") or "")
            tool = str(node.get("tool") or "")
            arguments = node.get("arguments") or {}
            properties = (
                (tool_schemas.get(tool) or {}).get("properties") or {}
            )
            if isinstance(arguments, dict):
                for argument, binding in arguments.items():
                    target = properties.get(argument)
                    visit_binding(
                        binding,
                        node_id=node_id,
                        tool=tool,
                        argument=str(argument),
                        target_schema=target if isinstance(target, dict) else None,
                        in_catch=in_catch,
                        direct=(
                            isinstance(binding, dict)
                            and set(binding) == {"input_ref"}
                        ),
                    )
            for key in ("workflow", "then", "else", "body"):
                children = node.get(key)
                if isinstance(children, list):
                    visit_nodes(children, in_catch=in_catch)
            catch = node.get("catch")
            if isinstance(catch, list):
                visit_nodes(catch, in_catch=True)

    visit_nodes(workflow_plan.get("workflow") or [])
    report = {
        "schema_version": "agentorch-workflow-input-binding-report-v1",
        "passed": all(row["passed"] for row in rows),
        "binding_count": len(rows),
        "rows": rows,
    }
    report["report_hash"] = stable_json_hash(report)
    return report


def _workato_scalar_matches(value: Any, field: dict[str, Any]) -> bool:
    if value is None:
        # Workato required means key presence. Datapills may still resolve to
        # nil, so nullability is intentionally independent of ``optional``.
        return True
    declared = str(field.get("type") or "")
    conversion = str(field.get("parse_output") or "")
    if declared == "string":
        # Workato text controls coerce scalar authoring expressions to their
        # text representation.  Preserve that public adapter equivalence
        # instead of pinning the scorer to the pre-coercion Python type.
        return isinstance(value, (str, int, float, bool))
    if declared in {"date", "date_time"}:
        return isinstance(value, str)
    if declared == "integer":
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
        ) or (
            isinstance(value, float)
            and value.is_integer()
        ) or (
            conversion == "integer_conversion"
            and isinstance(value, str)
            and re.fullmatch(r"[-+]?\d+", value) is not None
        )
    if declared == "number":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
        ) or (
            conversion in {"float_conversion", "parse_numeric_output"}
            and isinstance(value, str)
            and re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", value) is not None
        ) or (
            conversion in {"float_conversion", "parse_numeric_output"}
            and isinstance(value, bool)
        )
    if declared == "boolean":
        # Workato checkbox controls serialize custom authoring values as the
        # strings "true"/"false" even when ``parse_output`` is absent or an
        # empty object.  They are the adapter's canonical boolean encoding,
        # not a distinct public string type.
        return isinstance(value, bool) or (
            isinstance(value, str)
            and value.lower() in {"true", "false"}
        )
    if declared == "object":
        return isinstance(value, dict)
    return True


def _validate_workato_body(
    body: Any,
    fields: list[dict[str, Any]],
    *,
    path: str,
) -> list[str]:
    if not isinstance(body, dict):
        return [f"{path} has type {_json_type(body)}, expected object"]
    declared = {
        str(field.get("name")): field
        for field in fields
        if isinstance(field, dict) and field.get("name")
    }
    # Workato authoring schemas may encode an object path as one field name
    # containing ``/`` while the runtime terminal argument uses the equivalent
    # nested JSON object.  Compare those representations semantically instead
    # of treating the container as an undeclared response key.
    # ``_row_id``/``_created_by`` are simulator storage metadata occasionally
    # carried through an unprojected table-record datapill.  They are not part
    # of the connector's public record schema and therefore cannot participate
    # in public terminal-interface closure.
    comparable_body = {
        key: value for key, value in body.items() if not str(key).startswith("_")
    }
    slash_roots: set[str] = set()
    for name in declared:
        if "/" not in name or name in comparable_body:
            continue
        parts = name.split("/")
        slash_roots.add(parts[0])
        current: Any = body
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                break
            current = current[part]
        else:
            comparable_body[name] = current
    for root in slash_roots:
        if root not in declared:
            comparable_body.pop(root, None)
    body = comparable_body
    required = {
        name
        for name, field in declared.items()
        if field.get("optional") is False
    }
    errors = [f"{path}.{name} is required" for name in sorted(required - set(body))]
    errors.extend(
        f"{path}.{name} is not declared" for name in sorted(set(body) - set(declared))
    )
    for name, value in body.items():
        field = declared.get(name)
        if field is None:
            continue
        field_path = f"{path}.{name}"
        if field.get("type") == "array":
            if value is None:
                continue
            if isinstance(value, dict) and field.get("of") == "object":
                # Workato represents a mapped list argument as one exemplar
                # object, optionally carrying ``____source`` for the source
                # collection.  It is an array projection, not an object-valued
                # response contract violation.
                value = [
                    {
                        key: child
                        for key, child in value.items()
                        if key != "____source"
                    }
                ]
            if not isinstance(value, list):
                errors.append(f"{field_path} has type {_json_type(value)}, expected array")
                continue
            child_fields = field.get("properties") or []
            if field.get("of") == "object" and isinstance(child_fields, list):
                for index, child in enumerate(value):
                    errors.extend(
                        _validate_workato_body(
                            child,
                            child_fields,
                            path=f"{field_path}[{index}]",
                        )
                    )
            continue
        if not _workato_scalar_matches(value, field):
            errors.append(
                f"{field_path} has type {_json_type(value)}, expected {field.get('type')}"
            )
    return errors


def terminal_interface_report(
    public_output_schema: dict[str, Any],
    variants: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate every executed public terminal response, including errors."""

    declared = [
        item
        for item in public_output_schema.get("declared_responses") or []
        if isinstance(item, dict)
    ]
    rows: list[dict[str, Any]] = []
    for variant in variants:
        variant_id = str(variant.get("variant_id") or "")
        for event in (variant.get("active_trace") or {}).get("events") or []:
            if not isinstance(event, dict) or event.get("event_type") != "tool_call":
                continue
            tool = str(event.get("tool") or "")
            args = event.get("arguments") or {}
            if tool == "workato_service.send_reply":
                if args.get("reply_type") == "error":
                    errors = []
                    if not isinstance(args.get("message"), str):
                        errors.append("service error reply requires string message")
                else:
                    candidates = [item for item in declared if item.get("kind") == "service_reply"]
                    errors = ["no declared service_reply output schema"]
                    for candidate in candidates:
                        candidate_errors = _validate_workato_body(
                            args.get("reply") or {},
                            candidate.get("body_schema") or [],
                            path="$.reply",
                        )
                        if not candidate_errors:
                            errors = []
                            break
                        errors = candidate_errors
            elif tool == "workato_api_platform.return_response":
                status = str(args.get("http_status_code") or "")
                candidates = [
                    item for item in declared
                    if str(item.get("http_status_code") or "") == status
                ]
                errors = [f"no declared API response for HTTP status {status}"]
                for candidate in candidates:
                    candidate_errors = _validate_workato_body(
                        args.get("response") or {},
                        candidate.get("body_schema") or [],
                        path="$.response",
                    )
                    if not candidate_errors:
                        errors = []
                        break
                    errors = candidate_errors
            else:
                continue
            rows.append(
                {
                    "variant_id": variant_id,
                    "tool": tool,
                    "passed": not errors,
                    "errors": errors,
                }
            )

    report = {
        "schema_version": "agentorch-terminal-interface-report-v1",
        "passed": all(row["passed"] for row in rows),
        "checked_terminal_count": len(rows),
        "rows": rows,
        "nullability_policy": (
            "declared key presence is enforced; Workato datapill nil is allowed "
            "independently of the authoring optional flag"
        ),
        "simulator_metadata_policy": (
            "underscore-prefixed simulator storage metadata is excluded from the "
            "public terminal interface"
        ),
    }
    report["report_hash"] = stable_json_hash(report)
    return report
