"""Deterministic Stage-1-to-WorkflowPlanV1 compiler.

This module deliberately consumes only the versioned Stage 1 artifact.  It
does not inspect TaskSpec, Q, model annotations, or runtime variants when it
decides which nodes belong in canonical ground truth.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from copy import deepcopy
from typing import Any, Iterable

from .pipeline_common import stable_json_hash
from .tool_catalog import ToolCatalog
from .canonical_tool_arguments import canonical_tool_arguments
from .workato_formula import WorkatoFormulaError, project_workato_formula


WORKFLOW_PLAN_SCHEMA_VERSION = "agentorch-workflow-plan-v1"
COMPILER_VERSION = "workflow-a-compiler-v2"
DERIVED_INDEX_VERSION = "workflow-a-derived-index-v1"

STRUCTURAL_KINDS = {
    "if",
    "elsif",
    "else",
    "foreach",
    "repeat",
    "while_condition",
    "try",
    "catch",
    "stop",
    "terminal_result",
}
CALL_KINDS = {"tool", "terminal_response"}

_DATAPILL_RE = re.compile(r"#\{_dp\('(.+?)'\)\}")
_FORMULA_DATAPILL_RE = re.compile(r"^=_dp\('(.+)'\)$")


class WorkflowGroundtruthError(ValueError):
    """The Stage 1 artifact cannot be compiled without guessing."""


def _walk(nodes: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for node in nodes:
        if not isinstance(node, dict):
            continue
        yield node
        body = node.get("body")
        if isinstance(body, list):
            yield from _walk(body)


def _execution_nodes(stage1: dict[str, Any]) -> list[dict[str, Any]]:
    body = stage1.get("body")
    if not isinstance(body, list):
        raise WorkflowGroundtruthError("Stage 1 artifact has no canonical body")
    nodes = list(_walk(body))
    identifiers = [str(node.get("node_id") or "") for node in nodes]
    if any(not value for value in identifiers):
        raise WorkflowGroundtruthError("canonical node is missing node_id")
    if len(identifiers) != len(set(identifiers)):
        raise WorkflowGroundtruthError("canonical node_id values are not unique")
    return nodes


def _runtime_class(node: dict[str, Any], catalog: ToolCatalog) -> str:
    if node.get("skip") is True:
        return "skipped_or_unreachable"
    kind = str(node.get("kind") or "")
    if kind in CALL_KINDS:
        raw_tool = str(node.get("tool_name") or "")
        if not raw_tool:
            raise WorkflowGroundtruthError(
                f"{node.get('node_id')} is executable but has no tool_name"
            )
        status = catalog.status(raw_tool, node)
        if status not in {"registered", "runtime_internal"}:
            raise WorkflowGroundtruthError(
                f"{node.get('node_id')} has no supported public capability: "
                f"{raw_tool}"
            )
        return "model_action"
    if kind in STRUCTURAL_KINDS:
        return "structural_control"
    raise WorkflowGroundtruthError(
        f"{node.get('node_id')} has unsupported canonical kind {kind!r}"
    )


def derived_indexes(
    stage1: dict[str, Any],
    catalog: ToolCatalog,
) -> dict[str, Any]:
    """Build the versioned cached views required by the redesign."""

    canonical = _execution_nodes(stage1)
    data_predecessors: dict[str, set[str]] = defaultdict(set)
    control_predecessors: dict[str, set[str]] = defaultdict(set)
    for edge in stage1.get("data_flow_edges") or []:
        if isinstance(edge, dict) and edge.get("from") and edge.get("to"):
            data_predecessors[str(edge["to"])].add(str(edge["from"]))
    for edge in stage1.get("control_flow_edges") or []:
        if isinstance(edge, dict) and edge.get("from") and edge.get("to"):
            control_predecessors[str(edge["to"])].add(str(edge["from"]))

    rows: list[dict[str, Any]] = []
    for index, node in enumerate(canonical, 1):
        node_id = str(node["node_id"])
        path_conditions = node.get("path_conditions") or []
        control_path = [
            {
                "controller": str(item.get("controller") or ""),
                "branch": str(item.get("branch") or ""),
            }
            for item in path_conditions
            if isinstance(item, dict)
        ]
        loop_stack = [
            item["controller"]
            for item in control_path
            if item["branch"] in {"loop_body", "repeat_body", "iteration"}
        ]
        protected_by = node.get("protected_by")
        exception_branch = next(
            (
                item["branch"]
                for item in reversed(control_path)
                if item["branch"] in {"try_success", "exception"}
            ),
            None,
        )
        if protected_by:
            exception_region: dict[str, Any] = {
                "region": "try",
                "controller": str(protected_by),
            }
        elif exception_branch == "exception":
            controller = next(
                item["controller"]
                for item in reversed(control_path)
                if item["branch"] == "exception"
            )
            exception_region = {"region": "catch", "controller": controller}
        else:
            exception_region = {"region": "outside", "controller": None}
        rows.append(
            {
                "node_id": node_id,
                "execution_index": index,
                "runtime_class": _runtime_class(node, catalog),
                "control_path": control_path,
                "loop_stack": loop_stack,
                "exception_region": exception_region,
                "direct_dependencies": {
                    "data": sorted(data_predecessors[node_id]),
                    "control": sorted(control_predecessors[node_id]),
                },
            }
        )
    payload = {
        "schema_version": DERIVED_INDEX_VERSION,
        "workflow_a_hash": stage1.get("workflow_A_hash"),
        "indexes": rows,
    }
    payload["derived_indexes_hash"] = stable_json_hash(payload)
    return payload


def _raw_datapill(value: str) -> dict[str, Any] | None:
    try:
        decoded = json.loads(value.replace("\\'", "'"))
    except json.JSONDecodeError:
        return None
    return decoded if isinstance(decoded, dict) else None


def _path_parts(value: Any) -> list[str]:
    result: list[str] = []
    for item in value if isinstance(value, list) else []:
        if isinstance(item, (str, int)):
            result.append(str(item))
        elif isinstance(item, dict) and item.get("path_element_type"):
            path_type = str(item["path_element_type"])
            if path_type == "join":
                # Salesforce related-record datapills do not execute a
                # separate connector call. The search result already carries
                # the expanded relationship under Account__r/Account-style
                # keys. Preserve that deterministic path instead of the
                # lossy generic ``<join>`` marker.
                source_key = str(item.get("src_key") or "")
                relationship = (
                    source_key[:-3] + "__r"
                    if source_key.endswith("__c")
                    else source_key.removesuffix("Id")
                )
                if not relationship:
                    raise WorkflowGroundtruthError(
                        "join datapill is missing its source relationship key"
                    )
                result.append(relationship)
            else:
                result.append(f"<{path_type}>")
    return result


def _reference(
    datapill: dict[str, Any],
    source_as_to_plan: dict[str, Any],
    source_as_to_node: dict[str, str],
    catch_as_to_try_plan: dict[str, str],
    current_item_refs: dict[str, dict[int, str]] | None = None,
) -> dict[str, Any]:
    provider = str(datapill.get("provider") or "")
    line = str(datapill.get("line") or "")
    path = _path_parts(datapill.get("path"))
    current_item_refs = current_item_refs or {}
    pill_type = str(datapill.get("pill_type") or "")
    if pill_type == "foreach_meta" and not path and datapill.get("key"):
        path = [str(datapill["key"])]
    if line in current_item_refs and "<current_item>" in path:
        bindings = current_item_refs[line]
        markers = [
            index for index, item in enumerate(path)
            if item == "<current_item>"
        ]
        # Bind each explicit source-map level lexically.  When a datapill
        # contains a deeper current_item hop without a matching nested
        # ____source map, retain that remaining hop as an ordinary lookup on
        # the current outer row instead of flattening it to a sibling field.
        depth = max(
            (candidate for candidate in bindings if candidate <= len(markers)),
            default=0,
        )
        if not depth:
            raise WorkflowGroundtruthError(
                f"no source-map binding for current_item depth on line {line}"
            )
        marker = markers[depth - 1]
        reference: dict[str, Any] = {
            "loop_ref": {
                "source_node": bindings[depth],
                "path": path[marker + 1 :],
            }
        }
        if any("/" in part for part in path[marker + 1 :]):
            return {
                "expression": {
                    "op": "ruby_or",
                    "args": [reference, {"literal": ""}],
                }
            }
        return reference
    if line in current_item_refs and "first" in path:
        # Within a source map the editor can spell its current-row datapill
        # as `.first`. The map context, rather than the full collection,
        # determines that row.
        marker = path.index("first")
        binding = current_item_refs[line].get(1)
        if binding:
            reference = {
                "loop_ref": {
                    "source_node": binding,
                    "path": path[marker + 1 :],
                }
            }
            if any("/" in part for part in path[marker + 1 :]):
                return {
                    "expression": {
                        "op": "ruby_or",
                        "args": [reference, {"literal": ""}],
                    }
                }
            return reference
    if pill_type == "job_context":
        return {"input_ref": ".".join(["execution_context", *path])}
    if pill_type in {"account_property", "project_property"}:
        property_name = str(datapill.get("property_name") or "").strip()
        if property_name:
            container = (
                "account_properties"
                if pill_type == "account_property"
                else "project_properties"
            )
            return {
                "input_ref": ".".join(
                    [
                        "execution_context",
                        "workspace_configuration",
                        container,
                        property_name,
                    ]
                )
            }
    if provider == "catch" and line in catch_as_to_try_plan:
        return {
            "error_ref": {
                "source_node": catch_as_to_try_plan[line],
                "path": path,
            }
        }
    if line in source_as_to_plan:
        source_binding = source_as_to_plan[line]
        state_nodes = (
            [str(item) for item in source_binding.get("state_nodes") or [] if item]
            if isinstance(source_binding, dict)
            else []
        )
        if state_nodes:
            # Workato variable datapills address one mutable recipe-local
            # variable line.  An update action returns only the fields written
            # by that action, and the same update node can run again in a
            # repeat loop.  Select the newest executed writer that actually
            # contains this path, falling back to the declaration/earlier
            # writer.  ``path_exists`` deliberately differs from Ruby
            # presence: an explicitly written null/false/blank value still
            # belongs to the newest state.
            selected: dict[str, Any] = {
                "output_ref": {"node": state_nodes[0], "path": path}
            }
            for node_id in state_nodes[1:]:
                candidate = {
                    "output_ref": {"node": node_id, "path": path}
                }
                selected = {
                    "expression": {
                        "op": "if",
                        "condition": {
                            "expression": {
                                "op": "path_exists",
                                "args": [
                                    {
                                        "output_ref": {
                                            "node": node_id,
                                            "path": [],
                                        }
                                    }
                                ],
                                "path": path,
                            }
                        },
                        "args": [candidate, selected],
                    }
                }
            return selected
        if isinstance(source_binding, dict):
            source_node = str(source_binding.get("node") or "")
            path_prefix = list(source_binding.get("path_prefix") or [])
        else:
            source_node = str(source_binding)
            path_prefix = []
        value: dict[str, Any] = {
            "node": source_node,
            "path": [*path_prefix, *path],
        }
        return {"output_ref": value}
    if provider in {"foreach", "repeat"}:
        return {
            "loop_ref": {
                "source_node": source_as_to_node.get(line, line),
                "path": path,
            }
        }
    if path:
        return {"input_ref": ".".join(path)}
    return {
        "expression": {
            "op": "unresolved_public_reference",
            "provider": provider,
            "line": line,
        }
    }


def _source_mapping_line(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    formula_match = _FORMULA_DATAPILL_RE.fullmatch(value)
    if formula_match:
        parsed = _raw_datapill(formula_match.group(1))
        return str((parsed or {}).get("line") or "")
    match = _DATAPILL_RE.search(value)
    if match:
        parsed = _raw_datapill(match.group(1))
        return str((parsed or {}).get("line") or "")
    return ""


def _source_mapping_depth(value: Any) -> int:
    """Return the current-item depth introduced by one ____source value."""

    if not isinstance(value, str):
        return 1
    formula_match = _FORMULA_DATAPILL_RE.fullmatch(value)
    match = formula_match or _DATAPILL_RE.search(value)
    if not match:
        return 1
    parsed = _raw_datapill(match.group(1))
    path = _path_parts((parsed or {}).get("path"))
    return path.count("<current_item>") + 1


def _typed_value(
    value: Any,
    source_as_to_plan: dict[str, Any],
    source_as_to_node: dict[str, str],
    catch_as_to_try_plan: dict[str, str],
    current_item_refs: dict[str, dict[int, str]] | None = None,
) -> dict[str, Any]:
    current_item_refs = current_item_refs or {}
    if isinstance(value, str):
        try:
            formula = project_workato_formula(
                value,
                lambda datapill: _reference(
                    datapill,
                    source_as_to_plan,
                    source_as_to_node,
                    catch_as_to_try_plan,
                    current_item_refs,
                ),
            )
        except WorkatoFormulaError as exc:
            raise WorkflowGroundtruthError(
                f"unsupported Workato formula {value[:160]!r}: {exc}"
            ) from exc
        if formula is not None:
            return formula
        formula_match = _FORMULA_DATAPILL_RE.fullmatch(value)
        if formula_match:
            parsed = _raw_datapill(formula_match.group(1))
            if parsed is not None:
                return _reference(
                    parsed,
                    source_as_to_plan,
                    source_as_to_node,
                    catch_as_to_try_plan,
                    current_item_refs,
                )
        matches = list(_DATAPILL_RE.finditer(value))
        if len(matches) == 1 and matches[0].span() == (0, len(value)):
            parsed = _raw_datapill(matches[0].group(1))
            if parsed is not None:
                return _reference(
                    parsed,
                    source_as_to_plan,
                    source_as_to_node,
                    catch_as_to_try_plan,
                    current_item_refs,
                )
        if matches:
            parts: list[dict[str, Any]] = []
            cursor = 0
            for match in matches:
                if match.start() > cursor:
                    parts.append({"literal": value[cursor : match.start()]})
                parsed = _raw_datapill(match.group(1))
                parts.append(
                    _reference(
                        parsed,
                        source_as_to_plan,
                        source_as_to_node,
                        catch_as_to_try_plan,
                        current_item_refs,
                    )
                    if parsed is not None
                    else {"literal": match.group(0)}
                )
                cursor = match.end()
            if cursor < len(value):
                parts.append({"literal": value[cursor:]})
            return {"expression": {"op": "interpolate", "parts": parts}}
        return {"literal": value}
    if value is None or isinstance(value, (bool, int, float)):
        return {"literal": value}
    if isinstance(value, list):
        return {
            "expression": {
                "op": "array",
                "items": [
                    _typed_value(
                        item,
                        source_as_to_plan,
                        source_as_to_node,
                        catch_as_to_try_plan,
                        current_item_refs,
                    )
                    for item in value
                ],
            }
        }
    if isinstance(value, dict):
        for marker, op in (
            ("____canonical_slack_text", "slack_text"),
            ("____canonical_slack_attachments", "slack_attachments"),
            ("____canonical_salesforce_sobject", "salesforce_sobject"),
            ("____canonical_schema_boolean", "schema_boolean"),
            ("____canonical_workato_text", "workato_text"),
        ):
            if set(value) == {marker}:
                return {
                    "expression": {
                        "op": op,
                        "args": [
                            _typed_value(
                                value[marker],
                                source_as_to_plan,
                                source_as_to_node,
                                catch_as_to_try_plan,
                                current_item_refs,
                            )
                        ],
                    }
                }
        if "____source" in value:
            source_value = value.get("____source")
            source_line = _source_mapping_line(source_value)
            if not source_line:
                raise WorkflowGroundtruthError(
                    "____source mapping has no deterministic source datapill"
                )
            prior_bindings = current_item_refs.get(source_line, {})
            item_depth = _source_mapping_depth(source_value)
            item_bind = "map_%s_item_%d" % (
                re.sub(r"[^A-Za-z0-9_]", "_", source_line)[:24],
                item_depth,
            )
            item_refs = {
                **current_item_refs,
                source_line: {**prior_bindings, item_depth: item_bind},
            }
            template = {
                str(key): item
                for key, item in value.items()
                if key != "____source"
            }
            return {
                "expression": {
                    "op": "map",
                    "args": [
                        _typed_value(
                            source_value,
                            source_as_to_plan,
                            source_as_to_node,
                            catch_as_to_try_plan,
                            current_item_refs,
                        )
                    ],
                    "item_bind": item_bind,
                    "value": _typed_value(
                        template,
                        source_as_to_plan,
                        source_as_to_node,
                        catch_as_to_try_plan,
                        item_refs,
                    ),
                }
            }
        return {
            "expression": {
                "op": "object",
                "fields": {
                    str(key): _typed_value(
                        item,
                        source_as_to_plan,
                        source_as_to_node,
                        catch_as_to_try_plan,
                        current_item_refs,
                    )
                    for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
                },
            }
        }
    raise WorkflowGroundtruthError(f"unsupported argument value: {type(value)}")


def _workato_skip_value() -> dict[str, Any]:
    return {"expression": {"op": "workato_skip", "args": []}}


def _conditional_value(
    condition: dict[str, Any],
    positive: dict[str, Any],
) -> dict[str, Any]:
    return {
        "expression": {
            "op": "if",
            "condition": condition,
            "args": [positive, _workato_skip_value()],
        }
    }


def _apply_runtime_argument_omission(
    tool: str,
    arguments: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Encode connector nil/presence compaction in the symbolic plan."""

    projected = deepcopy(arguments)
    if tool == "workato_db_table.get_records" and "continuation_token" in projected:
        token = projected["continuation_token"]
        projected["continuation_token"] = {
            "expression": {
                "op": "if",
                "condition": {
                    "expression": {
                        "op": "ne",
                        "args": [deepcopy(token), {"literal": None}],
                    }
                },
                "args": [token, {"literal": ""}],
            }
        }
    if tool == "salesforce.search_records":
        limit = projected.get("limit")
        if limit is not None and not (
            isinstance(limit, dict)
            and set(limit) == {"literal"}
            and isinstance(limit.get("literal"), int)
        ):
            projected["limit"] = {
                "expression": {
                    "op": "canonical_optional_integer",
                    "args": [limit],
                }
            }
        filters = projected.get("filters")
        expression = filters.get("expression") if isinstance(filters, dict) else None
        if isinstance(expression, dict) and expression.get("op") == "array":
            retained: list[dict[str, Any]] = []
            for item in expression.get("items") or []:
                item_expression = (
                    item.get("expression") if isinstance(item, dict) else None
                )
                value = (
                    (item_expression.get("fields") or {}).get("value")
                    if isinstance(item_expression, dict)
                    and item_expression.get("op") == "object"
                    else None
                )
                if value is None:
                    retained.append(item)
                    continue
                retained.append(
                    _conditional_value(
                        {
                            "expression": {
                                "op": "is_present",
                                "args": [deepcopy(value)],
                            }
                        },
                        item,
                    )
                )
            filtered_array = {
                "expression": {"op": "array", "items": retained}
            }
            # Some adapters explicitly emit ``filters: []``. Preserve that
            # exact call shape when the source has no filter slots; compact
            # only a non-empty editor filter list whose values are dynamic.
            projected["filters"] = (
                _conditional_value(
                    {
                        "expression": {
                            "op": "is_present",
                            "args": [deepcopy(filtered_array)],
                        }
                    },
                    filtered_array,
                )
                if retained
                else filtered_array
            )
    if tool in {"snowflake.search_rows", "snowflake.search_rows_sql"}:
        for key in ("limit", "offset"):
            value = projected.get(key)
            if value is None or (
                isinstance(value, dict)
                and set(value) == {"literal"}
                and (value.get("literal") is None or isinstance(value.get("literal"), int))
            ):
                continue
            projected[key] = {
                "expression": {
                    "op": "canonical_optional_integer",
                    "args": [value],
                }
            }
    if tool in {
        "salesforce.create_record",
        "salesforce.update_record",
        "salesforce.upsert_record",
    }:
        fields = projected.get("fields")
        expression = fields.get("expression") if isinstance(fields, dict) else None
        if isinstance(expression, dict) and expression.get("op") == "object":
            expression["fields"] = {
                key: _conditional_value(
                    {
                        "expression": {
                            "op": "ne",
                            "args": [deepcopy(value), {"literal": None}],
                        }
                    },
                    value,
                )
                for key, value in (expression.get("fields") or {}).items()
            }
    return projected


def _split_conditional_body(
    body: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    positive: list[dict[str, Any]] = []
    negative: list[dict[str, Any]] = []
    for item in body:
        kind = str(item.get("kind") or "")
        if kind == "else":
            nested = item.get("body")
            if isinstance(nested, list):
                negative.extend(nested)
        elif kind == "elsif":
            negative.append(item)
        else:
            positive.append(item)
    return positive, negative


def _split_try_body(
    body: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    protected: list[dict[str, Any]] = []
    caught: list[dict[str, Any]] = []
    for item in body:
        if item.get("kind") == "catch":
            nested = item.get("body")
            if isinstance(nested, list):
                caught.extend(nested)
        else:
            protected.append(item)
    return protected, caught


def compile_workflow_plan(
    stage1: dict[str, Any],
    catalog: ToolCatalog,
) -> dict[str, Any]:
    """Compile one complete, contingent WorkflowPlanV1 from Stage 1 only."""

    indexes = derived_indexes(stage1, catalog)
    runtime_by_source = {
        row["node_id"]: row["runtime_class"] for row in indexes["indexes"]
    }
    canonical = _execution_nodes(stage1)
    plan_id_by_source = {
        str(node["node_id"]): f"n{index}"
        for index, node in enumerate(
            (
                node
                for node in canonical
                if runtime_by_source[str(node["node_id"])]
                != "skipped_or_unreachable"
                and str(node.get("kind") or "") not in {"else", "catch", "while_condition"}
            ),
            1,
        )
    }
    source_as_to_plan: dict[str, Any] = {
        str(node["source_as"]): (
            {
                "node": plan_id_by_source[str(node["node_id"])],
                "path_prefix": ["records", 0],
            }
            if str(node.get("tool_name") or "")
            == "salesforce.get_custom_object"
            else plan_id_by_source[str(node["node_id"])]
        )
        for node in canonical
        if node.get("source_as")
        and str(node["node_id"]) in plan_id_by_source
    }
    source_as_to_node = {
        str(node["source_as"]): str(node["node_id"])
        for node in canonical
        if node.get("source_as")
    }
    variable_declarations: list[tuple[int, str, str, set[str]]] = []
    for index, node in enumerate(canonical):
        if str(node.get("tool_name") or "") != "workato_variable.declare_variable":
            continue
        variables = (node.get("arguments") or {}).get("variables")
        variables = variables if isinstance(variables, dict) else {}
        fields = set((variables.get("data") or {}).keys()) if isinstance(
            variables.get("data"), dict
        ) else set()
        schema = variables.get("schema")
        if isinstance(schema, str):
            try:
                schema = json.loads(schema)
            except json.JSONDecodeError:
                schema = []
        for field in schema if isinstance(schema, list) else []:
            if isinstance(field, dict) and field.get("name"):
                fields.add(str(field["name"]))
        source_id = str(node.get("node_id") or "")
        plan_id = plan_id_by_source.get(source_id)
        if plan_id:
            variable_declarations.append((index, source_id, plan_id, fields))
    # Variable datapills use the variable-definition line token embedded in
    # an update action's ``name`` (not that action's own ``as`` token). Keep
    # every possible writer in lexical order: references resolve to the newest
    # executed writer containing the requested field, then fall back to the
    # declaration/earlier writer. This represents loop-carried variable state
    # without treating a partial update result as the complete object.
    for node_index, node in enumerate(canonical):
        source_id = str(node.get("node_id") or "")
        plan_id = plan_id_by_source.get(source_id)
        raw_tool = str(node.get("tool_name") or "")
        name = (node.get("arguments") or {}).get("name")
        if not plan_id or "workato_variable.update" not in raw_tool or not isinstance(name, str):
            continue
        variable_targets = {
            (parts[-2].strip(), parts[-1].strip())
            for raw_line in name.splitlines()
            if len(parts := raw_line.split(":")) >= 3
            and parts[-2].strip()
            and parts[-1].strip()
        }
        for variable_line, variable_field in sorted(variable_targets):
            declaration_source = ""
            existing = source_as_to_plan.get(variable_line)
            if isinstance(existing, dict) and "state_nodes" in existing:
                state_nodes = list(existing.get("state_nodes") or [])
            elif existing:
                state_nodes = [
                    str(existing.get("node") or "")
                    if isinstance(existing, dict)
                    else str(existing)
                ]
            else:
                declaration_candidates = [
                    (declaration_source, declaration_plan)
                    for (
                        declaration_index,
                        declaration_source,
                        declaration_plan,
                        fields,
                    ) in variable_declarations
                    if declaration_index < node_index and variable_field in fields
                ]
                state_nodes = (
                    [declaration_candidates[0][1]]
                    if len(declaration_candidates) == 1
                    else []
                )
                if len(declaration_candidates) == 1:
                    declaration_source = declaration_candidates[0][0]
            if plan_id not in state_nodes:
                state_nodes.append(plan_id)
            source_as_to_plan[variable_line] = {
                "state_nodes": [item for item in state_nodes if item]
            }
            source_as_to_node.setdefault(
                variable_line,
                declaration_source or source_id,
            )
    catch_as_to_try_plan: dict[str, str] = {}
    for node in canonical:
        if str(node.get("kind") or "") != "catch" or not node.get("source_as"):
            continue
        controller = next(
            (
                str(item.get("controller") or "")
                for item in reversed(node.get("path_conditions") or [])
                if isinstance(item, dict)
                and str(item.get("branch") or "") == "exception"
            ),
            "",
        )
        try_plan_id = plan_id_by_source.get(controller)
        if try_plan_id:
            catch_as_to_try_plan[str(node["source_as"])] = try_plan_id

    private_mapping: dict[str, str] = {}

    def foreach_batch_size(
        foreach_source: dict[str, Any],
        children: list[dict[str, Any]],
    ) -> Any:
        """Return the explicit connector batch size owned by this foreach.

        Workato serializes composite actions inside a foreach, but executes
        one connector call per configured batch.  The child action's
        ``batch_size`` is therefore loop control, not a connector argument,
        and must survive in WorkflowPlan rather than being discarded by the
        canonical connector projection.
        """

        source_as = str(foreach_source.get("source_as") or "")
        candidates: list[Any] = []
        for child in _walk(children):
            arguments = child.get("arguments") or {}
            if "batch_size" not in arguments:
                continue
            serialized = json.dumps(arguments, ensure_ascii=False, sort_keys=True)
            if (
                source_as
                and f'"line": "{source_as}"' not in serialized
                and f'\\"line\\":\\"{source_as}\\"' not in serialized
            ):
                continue
            if '"batch"' not in serialized and '\\"batch\\"' not in serialized:
                continue
            candidates.append(arguments.get("batch_size"))
        if not candidates:
            return None
        serialized_candidates = {
            json.dumps(value, ensure_ascii=False, sort_keys=True)
            for value in candidates
        }
        if len(serialized_candidates) != 1:
            raise WorkflowGroundtruthError(
                f"foreach {foreach_source.get('node_id')} has conflicting batch sizes"
            )
        value = candidates[0]
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return value

    def compile_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        compiled: list[dict[str, Any]] = []
        for source in nodes:
            source_id = str(source.get("node_id") or "")
            kind = str(source.get("kind") or "")
            if runtime_by_source.get(source_id) == "skipped_or_unreachable":
                continue
            if kind in {"else", "catch", "while_condition"}:
                continue
            plan_id = plan_id_by_source.get(source_id)
            if not plan_id:
                raise WorkflowGroundtruthError(
                    f"no deterministic plan ID for {source_id}"
                )
            private_mapping[plan_id] = source_id
            if kind in CALL_KINDS:
                raw_tool = str(source.get("tool_name") or "")
                tool = catalog.canonical_tool(raw_tool, source)
                public_arguments = canonical_tool_arguments(
                    tool,
                    source.get("arguments") or {},
                    redact_dynamic_values=False,
                    source_tool=raw_tool,
                    input_schema=source.get("input_schema"),
                    source_node=source,
                )
                typed_arguments = {
                    str(key): _typed_value(
                        value,
                        source_as_to_plan,
                        source_as_to_node,
                        catch_as_to_try_plan,
                    )
                    for key, value in sorted(public_arguments.items())
                }
                typed_arguments = _apply_runtime_argument_omission(
                    tool, typed_arguments
                )
                plan_call = {
                    "id": plan_id,
                    "kind": "call",
                    "tool": tool,
                    "arguments": typed_arguments,
                }
                if (
                    raw_tool == "google_sheets.add_row_v4_bulk"
                    and "rows" in typed_arguments
                ):
                    # One Workato bulk action fans out to one connector call
                    # per resolved row. Keep the original symbolic `rows`
                    # binding for lineage/fidelity, and make the connector
                    # expansion explicit so execution sends `data=<row>`.
                    plan_call["call_expansion"] = {
                        "collection_argument": "rows",
                        "item_argument": "data",
                    }
                compiled.append(plan_call)
                continue
            body = source.get("body")
            nested = body if isinstance(body, list) else []
            if kind in {"if", "elsif"}:
                then_source, else_source = _split_conditional_body(nested)
                compiled.append(
                    {
                        "id": plan_id,
                        "kind": "if",
                        "condition": _typed_value(
                            source.get("condition") or source.get("arguments") or {},
                            source_as_to_plan,
                            source_as_to_node,
                            catch_as_to_try_plan,
                        ),
                        "then": compile_nodes(then_source),
                        "else": compile_nodes(else_source),
                    }
                )
            elif kind == "foreach":
                loop = {
                    "id": plan_id,
                    "kind": "foreach",
                    "items": _typed_value(
                        (source.get("arguments") or {}).get("source"),
                        source_as_to_plan,
                        source_as_to_node,
                        catch_as_to_try_plan,
                    ),
                    "body": compile_nodes(nested),
                }
                batch_size = (
                    source.get("batch_size")
                    if source.get("repeat_mode") == "batch"
                    else foreach_batch_size(source, nested)
                )
                if batch_size is not None:
                    loop["batch_size"] = _typed_value(
                        batch_size,
                        source_as_to_plan,
                        source_as_to_node,
                        catch_as_to_try_plan,
                    )
                compiled.append(loop)
            elif kind == "repeat":
                while_node = next(
                    (item for item in nested if item.get("kind") == "while_condition"),
                    None,
                )
                compiled.append(
                    {
                        "id": plan_id,
                        "kind": "repeat",
                        "body": compile_nodes(
                            [item for item in nested if item is not while_node]
                        ),
                        "until": _typed_value(
                            (
                                while_node.get("condition")
                                if isinstance(while_node, dict)
                                else source.get("condition")
                            )
                            or {},
                            source_as_to_plan,
                            source_as_to_node,
                            catch_as_to_try_plan,
                        ),
                    }
                )
            elif kind == "try":
                protected, caught = _split_try_body(nested)
                compiled.append(
                    {
                        "id": plan_id,
                        "kind": "try",
                        "body": compile_nodes(protected),
                        "catch": compile_nodes(caught),
                    }
                )
            elif kind == "stop":
                compiled.append(
                    {
                        "id": plan_id,
                        "kind": "stop",
                        "arguments": _typed_value(
                            source.get("arguments") or {},
                            source_as_to_plan,
                            source_as_to_node,
                            catch_as_to_try_plan,
                        ),
                    }
                )
            elif kind == "terminal_result":
                compiled.append(
                    {
                        "id": plan_id,
                        "kind": "return",
                        "value": _typed_value(
                            source.get("arguments") or {},
                            source_as_to_plan,
                            source_as_to_node,
                            catch_as_to_try_plan,
                        ),
                    }
                )
            else:
                raise WorkflowGroundtruthError(
                    f"cannot compile {source_id} with kind {kind!r}"
                )
        return compiled

    workflow = compile_nodes(stage1["body"])
    plan = {
        "schema_version": WORKFLOW_PLAN_SCHEMA_VERSION,
        "recipe_id": str(stage1.get("recipe_id") or ""),
        "workflow": workflow,
        "compiler_version": COMPILER_VERSION,
        "workflow_a_hash": stage1.get("workflow_A_hash"),
    }
    plan["workflow_plan_hash"] = stable_json_hash(plan)
    return {
        "workflow_plan": plan,
        "derived_indexes": indexes,
        "private_source_mapping": private_mapping,
        "private_source_mapping_hash": stable_json_hash(private_mapping),
    }


def public_plan(compilation: dict[str, Any]) -> dict[str, Any]:
    """Return the publishable workflow target without source mappings."""

    return deepcopy(compilation["workflow_plan"])
