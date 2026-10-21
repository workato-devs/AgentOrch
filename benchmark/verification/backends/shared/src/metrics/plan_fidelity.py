"""Recipe-level symbolic workflow-plan fidelity metrics.

This evaluator is deliberately separate from runtime trace scoring.  It
compares a model-produced, variant-blind symbolic plan with the private
``WorkflowPlanV1`` reference and never renders or returns the reference as
model input.  ReAct has no recipe-level plan prediction and should therefore
continue to use active-trace metrics instead of this module.

The public result separates five orchestration dimensions:

* tool selection (multiset precision/recall/F1),
* control-aware partial order,
* conditions and control-flow placement,
* symbolic argument bindings, and
* overall plan-node coverage.

Node ids are intentionally ignored as labels.  They are aligned by typed node
occurrence, then candidate ``output_ref``/``loop_ref`` ids are rewritten only
inside the private evaluator before binding comparison.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Iterable


_CHILD_REGIONS: dict[str, tuple[str, ...]] = {
    "if": ("then", "else"),
    "foreach": ("body",),
    "repeat": ("body",),
    "try": ("body", "catch"),
}
_CONTROL_VALUE_FIELDS: dict[str, tuple[str, ...]] = {
    "if": ("condition",),
    "foreach": ("items",),
    "repeat": ("until",),
    "stop": ("arguments",),
    "return": ("value",),
}
_RUNTIME_QUERY_ARGUMENTS: dict[str, frozenset[str]] = {
    "salesforce.search_records": frozenset({"query", "filters", "limit"}),
    "snowflake.search_rows_sql": frozenset(
        {"sql", "parameters", "limit", "offset"}
    ),
    "snowflake.run_custom_sql": frozenset({"sql", "parameters"}),
}


class PlanFidelityError(ValueError):
    """A reference or candidate is not a scoreable workflow-plan AST."""


@dataclass(frozen=True)
class _Node:
    raw: dict[str, Any]
    node_id: str
    kind: str
    tool: str | None
    occurrence: int
    preorder: int
    parent_identity: tuple[str, ...] | None
    parent_region: str
    branch_regions: tuple[tuple[int, str], ...]

    @property
    def identity(self) -> tuple[str, ...]:
        if self.kind == "call":
            return ("call", str(self.tool or ""), str(self.occurrence))
        return (self.kind, str(self.occurrence))


def _workflow(value: Any, label: str) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = value.get("workflow", value.get("plan"))
    if not isinstance(value, list):
        raise PlanFidelityError(f"{label} must contain a workflow/plan array")
    if any(not isinstance(item, dict) for item in value):
        raise PlanFidelityError(f"{label} workflow nodes must be objects")
    return value


def _flatten(workflow: list[dict[str, Any]], label: str) -> list[_Node]:
    counts: Counter[tuple[str, str]] = Counter()
    nodes: list[_Node] = []
    seen_ids: set[str] = set()

    def visit(
        values: list[dict[str, Any]],
        parent: _Node | None,
        region: str,
        branch_regions: tuple[tuple[int, str], ...],
    ) -> None:
        for raw in values:
            kind = str(raw.get("kind") or "").strip()
            if not kind:
                raise PlanFidelityError(f"{label} contains a node without kind")
            tool = str(raw.get("tool") or "").strip() if kind == "call" else None
            if kind == "call" and not tool:
                raise PlanFidelityError(f"{label} contains a call without tool")
            node_id = str(raw.get("id") or f"__{label}_{len(nodes) + 1}")
            if node_id in seen_ids:
                raise PlanFidelityError(f"{label} contains duplicate node id {node_id!r}")
            seen_ids.add(node_id)
            count_key = (kind, tool or "")
            counts[count_key] += 1
            node = _Node(
                raw=raw,
                node_id=node_id,
                kind=kind,
                tool=tool,
                occurrence=counts[count_key],
                preorder=len(nodes),
                parent_identity=parent.identity if parent else None,
                parent_region=region,
                branch_regions=branch_regions,
            )
            nodes.append(node)
            for child_region in _CHILD_REGIONS.get(kind, ()):
                children = raw.get(child_region, [])
                if not isinstance(children, list) or any(
                    not isinstance(child, dict) for child in children
                ):
                    raise PlanFidelityError(
                        f"{label} {node_id}.{child_region} must be an array of nodes"
                    )
                child_branches = branch_regions
                if kind == "if":
                    child_branches += ((node.preorder, child_region),)
                visit(children, node, child_region, child_branches)

    visit(workflow, None, "workflow", ())
    return nodes


def _safe_div(numerator: int, denominator: int, *, empty: float) -> float:
    return numerator / denominator if denominator else empty


def _prf(expected: Counter[Any], actual: Counter[Any]) -> dict[str, Any]:
    matched = sum((expected & actual).values())
    expected_n = sum(expected.values())
    actual_n = sum(actual.values())
    precision = _safe_div(matched, actual_n, empty=1.0 if expected_n == 0 else 0.0)
    recall = _safe_div(matched, expected_n, empty=1.0)
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return {
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "exact": expected == actual,
        "matched_count": matched,
        "expected_count": expected_n,
        "actual_count": actual_n,
    }


def _canonical_typed_value(
    value: Any,
    id_map: dict[str, str],
    bind_map: dict[str, str] | None = None,
) -> Any:
    """Canonicalize typed-value spelling and remap candidate node references."""

    if isinstance(value, list):
        return [_canonical_typed_value(item, id_map, bind_map) for item in value]
    if not isinstance(value, dict):
        # A plain primitive in an argument position is an unambiguous literal.
        return {"literal": value}

    kind = value.get("kind")
    if isinstance(kind, str) and kind in {
        "literal",
        "input_ref",
        "output_ref",
        "resource_ref",
        "expression",
        "loop_ref",
        "error_ref",
    }:
        payload = {key: item for key, item in value.items() if key != "kind"}
        if kind == "literal" and set(payload) == {"value"}:
            value = {"literal": payload["value"]}
        elif kind == "input_ref":
            ref = payload.get("path", payload.get("value"))
            value = {"input_ref": ref}
        elif kind == "resource_ref":
            ref = payload.get("resource", payload.get("value", payload))
            value = {"resource_ref": ref}
        else:
            value = {kind: payload.get("value", payload)}

    if set(value) == {"literal"}:
        return {"literal": value["literal"]}
    if set(value) == {"input_ref"}:
        path = value["input_ref"]
        if isinstance(path, str):
            path = [part for part in path.split(".") if part]
        return {"input_ref": list(path) if isinstance(path, list) else path}
    if set(value) == {"resource_ref"} and isinstance(value["resource_ref"], str):
        return {"resource_ref": value["resource_ref"]}

    normalized: dict[str, Any] = {}
    for key in sorted(value):
        item = value[key]
        if key == "input_ref" and isinstance(item, str):
            item = [part for part in item.split(".") if part]
        if key in {"output_ref", "loop_ref", "error_ref"}:
            ref_key = "node" if key == "output_ref" else "source_node"
            if isinstance(item, str):
                item = {ref_key: (bind_map or {}).get(item, item)}
            elif isinstance(item, dict):
                item = dict(item)
                alias = item.pop(
                    "binding",
                    item.pop("bind", item.pop("name", None)),
                )
                if alias is not None and ref_key not in item:
                    item[ref_key] = (bind_map or {}).get(str(alias), str(alias))
                if ref_key in item:
                    ref = str(item[ref_key])
                    item[ref_key] = id_map.get(ref, (bind_map or {}).get(ref, ref))
        normalized[str(key)] = _canonical_typed_value(item, id_map, bind_map)

    # The recursive primitive rule above is for typed-value positions.  Undo
    # it inside representation dictionaries, whose scalar metadata (``op``,
    # ref path components, etc.) is already canonical data.
    normalized = _unwrap_metadata_literals(normalized)
    expression = normalized.get("expression")
    if isinstance(expression, dict) and expression.get("args") == [] and any(
        key in expression for key in ("parts", "fields", "items")
    ):
        expression.pop("args")
    if isinstance(expression, dict) and expression.get("op") == "object":
        fields = expression.get("fields") or {}
        if _literal_content(fields.get("type")) == "compound":
            conditions = fields.get("conditions") or {}
            condition_expression = conditions.get("expression") or {}
            raw_leaves = condition_expression.get("items") or []
            leaves: list[dict[str, Any]] = []
            for raw_leaf in raw_leaves:
                leaf_expression = (raw_leaf.get("expression") or {}) if isinstance(
                    raw_leaf, dict
                ) else {}
                leaf_fields = leaf_expression.get("fields") or {}
                operand = str(_literal_content(leaf_fields.get("operand")) or "")
                lhs = leaf_fields.get("lhs")
                rhs = leaf_fields.get("rhs")
                binary = {
                    "equals_to": "eq", "not_equals_to": "ne",
                    "greater_than": "gt", "less_than": "lt",
                }
                if operand in binary:
                    leaves.append({"expression": {
                        "op": binary[operand], "args": [lhs, rhs],
                    }})
                elif operand in {"present", "blank"}:
                    leaves.append({"expression": {
                        "op": "is_present" if operand == "present" else "is_blank",
                        "args": [lhs],
                    }})
                elif operand in {"is_true", "is_not_true"}:
                    leaves.append({"expression": {
                        "op": "eq" if operand == "is_true" else "ne",
                        "args": [lhs, {"literal": True}],
                    }})
                else:
                    methods = {
                        "contains": "include?", "not_contains": "include?",
                        "starts_with": "starts_with?", "ends_with": "ends_with?",
                        "not_ends_with": "ends_with?",
                    }
                    method = methods.get(operand)
                    if method is None:
                        continue
                    leaf: dict[str, Any] = {"expression": {
                        "op": "call_method",
                        "args": [lhs, {"literal": method}, rhs],
                    }}
                    if operand.startswith("not_"):
                        leaf = {"expression": {"op": "not", "args": [leaf]}}
                    leaves.append(leaf)
            connective = str(_literal_content(fields.get("operand")) or "and")
            if len(leaves) == 1:
                normalized = leaves[0]
            elif leaves and connective in {"and", "or"}:
                normalized = {"expression": {"op": connective, "args": leaves}}
    return normalized


def _literal_content(value: Any) -> Any:
    return value.get("literal") if isinstance(value, dict) and set(value) == {"literal"} else None


def _typed_object(fields: dict[str, Any]) -> dict[str, Any]:
    return {"expression": {"op": "object", "fields": fields}}


def _typed_array(items: list[Any]) -> dict[str, Any]:
    return {"expression": {"op": "array", "items": items}}


def _expression_fields(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    expression = value.get("expression")
    if not isinstance(expression, dict) or expression.get("op") != "object":
        return None
    fields = expression.get("fields")
    return fields if isinstance(fields, dict) else None


def _expression_items(value: Any) -> list[Any] | None:
    if not isinstance(value, dict):
        return None
    expression = value.get("expression")
    if not isinstance(expression, dict) or expression.get("op") != "array":
        return None
    items = expression.get("items")
    return items if isinstance(items, list) else None


def _normalize_db_record_fields(value: Any) -> Any:
    """Map authoring UUID dashes to the public simulator field spelling."""

    if isinstance(value, list):
        return [_normalize_db_record_fields(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: _normalize_db_record_fields(item) for key, item in value.items()}
    expression = result.get("expression")
    if isinstance(expression, dict) and expression.get("op") == "object" and isinstance(
        expression.get("fields"), dict
    ):
        expression["fields"] = {
            str(key).replace("-", "_"): item
            for key, item in expression["fields"].items()
        }
    return result


def _project_db_filters(value: Any) -> Any | None:
    items = _expression_items(value)
    if items is None:
        return None
    projected: list[Any] = []
    for item in items:
        fields = _expression_fields(item)
        if fields is None:
            return None
        operator_key = next((key for key in fields if str(key).startswith("op")), None)
        operator = fields.get(operator_key) if operator_key else {"literal": "eq"}
        raw_operator = str(_literal_content(operator) or "").lower()
        field_id = fields.get("field_id")
        if isinstance(field_id, dict) and isinstance(field_id.get("literal"), str):
            field_id = {"literal": field_id["literal"].replace("-", "_")}
        output = {"field_id": field_id, "op": operator}
        if raw_operator not in {"isnull", "isnotnull"}:
            suffix = str(operator_key or "op")[2:]
            value_key = f"value{suffix}"
            if value_key in fields:
                output["value"] = fields[value_key]
        projected.append(_typed_object(output))
    return _typed_array(projected)


def _active_public_argument_keys(bundle: Any) -> dict[str, set[str]] | None:
    """Return public simulator keys witnessed for each canonical plan node.

    A bare WorkflowPlan has no proof that its authoring arguments already use
    the public connector contract.  A full Stage-7 bundle does: ActiveTraceV1
    events are emitted after the private raw-to-public adapter.  We use only
    their key names, never concrete variant values.
    """

    if not isinstance(bundle, dict) or not isinstance(bundle.get("variants"), list):
        return None
    result: dict[str, set[str]] = defaultdict(set)
    for variant in bundle["variants"]:
        if not isinstance(variant, dict):
            continue
        trace = variant.get("active_trace") or {}
        for event in trace.get("events") or []:
            if not isinstance(event, dict) or event.get("event_type") != "tool_call":
                continue
            node_id = str(event.get("plan_node_ref") or "")
            arguments = event.get("arguments")
            if node_id and isinstance(arguments, dict):
                result[node_id].update(str(key) for key in arguments)
    return dict(result)


def _project_reference_arguments(
    node: _Node,
    public_keys: set[str],
) -> tuple[dict[str, Any], set[str]]:
    """Conservatively map raw Workato arguments to public symbolic bindings.

    The second return value names public bindings known to be required by an
    ActiveTrace adapter but not safely recoverable symbolically.  Such fields
    are excluded from the F1 denominator and force argument ``exact`` to
    ``None`` instead of producing either a false failure or false exactness.
    """

    raw = node.raw.get("arguments", node.raw.get("args", {}))
    if not isinstance(raw, dict):
        return {}, set(public_keys)
    if not public_keys and raw:
        return {}, {"__unwitnessed_public_contract__"}
    tool = str(node.tool or "")
    projected = {key: raw[key] for key in public_keys if key in raw}
    excluded: set[str] = set()

    if tool == "workato_db_table.get_records" and "filters" in public_keys:
        filters = _project_db_filters(raw.get("filters"))
        if filters is None:
            if "filters" in raw:
                projected.pop("filters", None)
                excluded.add("filters")
        else:
            projected["filters"] = filters

    if tool in {
        "workato_db_table.add_record",
        "workato_db_table.update_record",
        "workato_db_table.upsert_record",
    } and "record" in public_keys and "parameters" in raw:
        projected["record"] = _normalize_db_record_fields(raw["parameters"])

    if tool == "salesforce.search_records":
        sobject = raw.get("sobject", raw.get("sobject_name"))
        if "sobject" in public_keys and sobject is not None:
            projected["sobject"] = sobject
        if "query" in public_keys and "query" not in projected:
            projected["query"] = {"literal": ""}
        metadata = {
            "field_list", "limit", "offset", "output_schema", "query",
            "sobject", "sobject_name", "table_list",
        }
        filter_fields = [key for key in raw if key not in metadata]
        if "filters" in public_keys and filter_fields:
            projected["filters"] = _typed_array([
                _typed_object({
                    "field": {"literal": "Id" if key == "id" else key},
                    "value": raw[key],
                })
                for key in filter_fields
            ])

    if tool in {
        "salesforce.create_record",
        "salesforce.update_record",
        "salesforce.upsert_record",
    }:
        sobject = raw.get("sobject", raw.get("sobject_name"))
        if "sobject" in public_keys and sobject is not None:
            projected["sobject"] = sobject
        source = _expression_fields(raw.get("records"))
        if source is not None:
            if "id" in public_keys and "Id" in source:
                projected["id"] = source["Id"]
            fields = {
                key: value
                for key, value in source.items()
                if key not in {"Id", "id", "____source", "attributes"}
            }
            if "fields" in public_keys:
                projected["fields"] = _typed_object(fields)
        for key in ("id", "fields"):
            if key in public_keys and key not in projected:
                excluded.add(key)

    if tool in {"slack.post_message", "slack.post_reply"}:
        # Workato Block Kit authoring input is rendered to public ``text`` by a
        # non-trivial adapter. Until the compiler emits that symbolic public
        # form, do not compare ``blocks`` with ``text`` as if they were equal.
        if "text" in public_keys and "text" not in raw and "blocks" in raw:
            excluded.add("text")

    if tool == "slack_bot.generate_menu_options" and "options" in public_keys:
        # The private Workato representation embeds current-item datapills and
        # authoring-only ``____source`` metadata. A public plan represents the
        # same projection with map/transform + output_ref. Until the compiler
        # emits a shared canonical transform AST, this binding is intentionally
        # uncomparable rather than a false mismatch.
        options = raw.get("options")
        fields = _expression_fields(options)
        if isinstance(fields, dict) and (
            "____source" in fields
            or any("current_item" in _json_key(value) for value in fields.values())
        ):
            projected.pop("options", None)
            excluded.add("options")

    if "force" in public_keys and "force_stop" in raw:
        projected["force"] = raw["force_stop"]

    return projected, excluded


def _unwrap_metadata_literals(value: Any) -> Any:
    if isinstance(value, list):
        return [_unwrap_metadata_literals(item) for item in value]
    if not isinstance(value, dict):
        return value
    if set(value) == {"literal"}:
        # Retain the actual typed literal wrapper; callers rely on this shape.
        return {"literal": _unwrap_metadata_literals(value["literal"])}
    result: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, dict) and set(item) == {"literal"} and key in {
            "op",
            "node",
            "source_node",
        }:
            result[key] = item["literal"]
        elif key == "path" and isinstance(item, list):
            result[key] = [
                part.get("literal")
                if isinstance(part, dict) and set(part) == {"literal"}
                else _unwrap_metadata_literals(part)
                for part in item
            ]
        else:
            result[key] = _unwrap_metadata_literals(item)
    return result


def _json_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _symbolic_text(value: Any) -> str | None:
    """Render deterministic string expressions with stable reference tokens."""

    if not isinstance(value, dict):
        return None
    if set(value) == {"literal"}:
        return str(value["literal"])
    if set(value) == {"input_ref"}:
        path = value["input_ref"]
        if isinstance(path, str):
            path = [part for part in path.split(".") if part]
        return "{{input:" + ".".join(str(part) for part in path or []) + "}}"
    expression = value.get("expression")
    if isinstance(expression, dict) and expression.get("op") == "interpolate":
        rendered = [_symbolic_text(part) for part in expression.get("parts") or []]
        return None if any(part is None for part in rendered) else "".join(rendered)  # type: ignore[arg-type]
    return None


def _canonical_argument_value(
    tool: str,
    key: str,
    value: Any,
    id_map: dict[str, str],
    bind_map: dict[str, str] | None,
) -> Any:
    # Representation-only canonicalization for non-query slots: normalize
    # typed-value spelling and aligned node/bind identifiers, but preserve
    # argument value, scalar type, and list order. SQL/SOQL query surfaces are
    # excluded by ``_argument_bindings`` and verified after connector execution.
    canonical = _canonical_typed_value(value, id_map, bind_map)
    if key in {"sobject", "table_id", "channel"} and isinstance(canonical, dict):
        resource = canonical.get("resource_ref")
        if isinstance(resource, str):
            canonical = {"literal": resource}
    return canonical


def _id_alignment(reference: list[_Node], candidate: list[_Node]) -> dict[str, str]:
    reference_by_identity = {node.identity: node for node in reference}
    return {
        node.node_id: reference_by_identity[node.identity].node_id
        for node in candidate
        if node.identity in reference_by_identity
    }


def _bind_alignment(nodes: list[_Node], node_id_map: dict[str, str]) -> dict[str, str]:
    """Alpha-normalize output/item/error bind names to aligned node ids."""

    result: dict[str, str] = {}
    for node in nodes:
        aliases: list[str] = []
        for field in ("bind", "item_bind", "error_bind"):
            value = node.raw.get(field)
            if isinstance(value, str) and value:
                aliases.append(value)
            elif isinstance(value, dict):
                aliases.extend(str(item) for item in value.values() if item not in (None, ""))
        target = node_id_map.get(node.node_id, node.node_id)
        for alias in aliases:
            if alias in result:
                # The symbolic-plan validator permits a stable phi-style bind
                # to be defined once in each mutually exclusive branch. It is
                # a merged value after the conditional, not an invalid duplicate.
                result[alias] = f"__merged_bind__:{alias}"
            else:
                result[alias] = target
    return result


def _tool_selection(reference: list[_Node], candidate: list[_Node]) -> dict[str, Any]:
    expected = Counter(node.tool for node in reference if node.kind == "call")
    actual = Counter(node.tool for node in candidate if node.kind == "call")
    result = _prf(expected, actual)
    result["missing_tools"] = sorted((expected - actual).elements())
    result["extra_tools"] = sorted((actual - expected).elements())
    return result


def _mutually_exclusive(left: _Node, right: _Node) -> bool:
    left_regions = dict(left.branch_regions)
    right_regions = dict(right.branch_regions)
    return any(
        controller in right_regions and right_regions[controller] != region
        for controller, region in left_regions.items()
    )


def _precedence(nodes: Iterable[_Node]) -> set[tuple[tuple[str, ...], tuple[str, ...]]]:
    calls = [node for node in nodes if node.kind == "call"]
    return {
        (left.identity, right.identity)
        for left_index, left in enumerate(calls)
        for right in calls[left_index + 1 :]
        if not _mutually_exclusive(left, right)
    }


def _partial_order(reference: list[_Node], candidate: list[_Node]) -> dict[str, Any]:
    # Order is assessed only among calls selected by both plans.  A missing or
    # extraneous tool belongs to the selection axis and must not be charged a
    # second time as an ordering error.
    common = _node_counter(reference) & _node_counter(candidate)
    common_calls = {
        identity for identity in common if identity and identity[0] == "call"
    }
    expected = Counter(
        pair
        for pair in _precedence(reference)
        if pair[0] in common_calls and pair[1] in common_calls
    )
    actual = Counter(
        pair
        for pair in _precedence(candidate)
        if pair[0] in common_calls and pair[1] in common_calls
    )
    result = _prf(expected, actual)
    result["shared_call_count"] = len(common_calls)
    return result


def _node_counter(nodes: list[_Node]) -> Counter[tuple[str, ...]]:
    return Counter(node.identity for node in nodes)


def _control_edges(
    nodes: list[_Node],
    included: set[tuple[str, ...]],
) -> Counter[tuple[Any, ...]]:
    return Counter(
        (node.parent_identity, node.parent_region, node.identity)
        for node in nodes
        if node.identity in included
        and (node.parent_identity is None or node.parent_identity in included)
    )


def _control_values(
    nodes: list[_Node],
    id_map: dict[str, str],
    included: set[tuple[str, ...]],
    bind_map: dict[str, str] | None = None,
) -> Counter[tuple[Any, ...]]:
    values: Counter[tuple[Any, ...]] = Counter()
    for node in nodes:
        if node.identity not in included:
            continue
        for field in _CONTROL_VALUE_FIELDS.get(node.kind, ()):
            if field in node.raw:
                values[(
                    node.identity,
                    field,
                    _json_key(
                        _canonical_typed_value(node.raw[field], id_map, bind_map)
                    ),
                )] += 1
    return values


def _combine_counts(*pairs: tuple[Counter[Any], Counter[Any]]) -> dict[str, Any]:
    expected: Counter[Any] = Counter()
    actual: Counter[Any] = Counter()
    for index, (expected_part, actual_part) in enumerate(pairs):
        expected.update((index, item) for item in expected_part.elements())
        actual.update((index, item) for item in actual_part.elements())
    return _prf(expected, actual)


def _control_flow(
    reference: list[_Node],
    candidate: list[_Node],
    candidate_id_map: dict[str, str],
    reference_bind_map: dict[str, str],
    candidate_bind_map: dict[str, str],
) -> dict[str, Any]:
    expected_nodes = Counter(
        node.identity for node in reference if node.kind != "call"
    )
    actual_nodes = Counter(
        node.identity for node in candidate if node.kind != "call"
    )
    # Placement is compared for aligned nodes.  This isolates control-flow
    # quality from tool selection while still penalizing missing/extra control
    # nodes through ``expected_nodes``/``actual_nodes``.
    included = set((_node_counter(reference) & _node_counter(candidate)).keys())
    expected_edges = _control_edges(reference, included)
    actual_edges = _control_edges(candidate, included)
    common_controls = {
        identity for identity in included if identity and identity[0] != "call"
    }
    expected_values = _control_values(
        reference, {}, common_controls, reference_bind_map
    )
    actual_values = _control_values(
        candidate, candidate_id_map, common_controls, candidate_bind_map
    )
    result = _combine_counts(
        (expected_nodes, actual_nodes),
        (expected_edges, actual_edges),
        (expected_values, actual_values),
    )
    result["node_structure"] = _prf(expected_nodes, actual_nodes)
    result["placement_edges"] = _prf(expected_edges, actual_edges)
    result["condition_bindings"] = _prf(expected_values, actual_values)
    return result


def _argument_bindings(
    nodes: list[_Node],
    id_map: dict[str, str],
    included: set[tuple[str, ...]],
    *,
    argument_overrides: dict[str, dict[str, Any]] | None = None,
    comparable_keys: dict[tuple[str, ...], set[str]] | None = None,
    bind_map: dict[str, str] | None = None,
) -> Counter[tuple[Any, ...]]:
    bindings: Counter[tuple[Any, ...]] = Counter()
    for node in nodes:
        if node.kind != "call" or node.identity not in included:
            continue
        arguments = (
            argument_overrides[node.node_id]
            if argument_overrides is not None and node.node_id in argument_overrides
            else node.raw.get("arguments", node.raw.get("args", {}))
        )
        if not isinstance(arguments, dict):
            # Invalid argument containers become one non-matching atom rather
            # than disappearing and inflating recall.
            bindings[(node.identity, "__invalid_arguments__", _json_key(arguments))] += 1
            continue
        semantic_keys = _RUNTIME_QUERY_ARGUMENTS.get(str(node.tool or ""))
        comparable = (
            comparable_keys.get(node.identity, set())
            if comparable_keys is not None
            else None
        )
        if semantic_keys is not None and (
            comparable is None or bool(semantic_keys & comparable)
        ):
            anchor_keys = (
                {"query", "filters"}
                if node.tool == "salesforce.search_records"
                else {"sql"}
            )
            if anchor_keys & set(map(str, arguments)):
                bindings[(
                    node.identity,
                    "__query_semantics__",
                    "runtime_result_or_state",
                )] += 1
        for key, value in arguments.items():
            if semantic_keys is not None and str(key) in semantic_keys:
                # SQL/SOQL syntax is intentionally not scored at plan time.
                # The executed connector call is scored against all hidden
                # variants by result/state semantics instead.
                continue
            if comparable_keys is not None and str(key) not in comparable_keys.get(
                node.identity, set()
            ):
                continue
            bindings[(
                node.identity,
                str(key),
                _json_key(
                    _canonical_argument_value(
                        str(node.tool or ""),
                        str(key),
                        value,
                        id_map,
                        bind_map,
                    )
                ),
            )] += 1
    return bindings


def evaluate_plan_fidelity(reference_plan: Any, candidate_plan: Any) -> dict[str, Any]:
    """Score one variant-blind candidate against private recipe-level gold.

    ``reference_plan`` may be the full private ground-truth bundle, its
    ``workflow_plan`` member, or a plan object/list. ``candidate_plan`` may be
    an artifact containing ``plan`` or a plan object/list.  The returned object
    contains only aggregate metrics and mismatch labels; it must be stored in
    evaluator output, never incorporated into a later model prompt.
    """

    reference_bundle = reference_plan
    public_argument_keys = _active_public_argument_keys(reference_bundle)
    if isinstance(reference_bundle, dict) and isinstance(
        reference_bundle.get("workflow_plan"), dict
    ):
        reference_plan = reference_bundle["workflow_plan"]
    reference = _flatten(_workflow(reference_plan, "reference"), "reference")
    candidate = _flatten(_workflow(candidate_plan, "candidate"), "candidate")
    candidate_id_map = _id_alignment(reference, candidate)
    reference_bind_map = _bind_alignment(reference, {})
    candidate_bind_map = _bind_alignment(candidate, candidate_id_map)

    tool_selection = _tool_selection(reference, candidate)
    partial_order = _partial_order(reference, candidate)
    control_flow = _control_flow(
        reference,
        candidate,
        candidate_id_map,
        reference_bind_map,
        candidate_bind_map,
    )
    common_calls = {
        identity
        for identity in (_node_counter(reference) & _node_counter(candidate))
        if identity and identity[0] == "call"
    }
    reference_argument_overrides: dict[str, dict[str, Any]] | None = None
    comparable_argument_keys: dict[tuple[str, ...], set[str]] | None = None
    excluded_bindings: list[str] = []
    if public_argument_keys is not None:
        reference_argument_overrides = {}
        comparable_argument_keys = {}
        for node in reference:
            if node.kind != "call" or node.identity not in common_calls:
                continue
            projected, excluded = _project_reference_arguments(
                node,
                public_argument_keys.get(node.node_id, set()),
            )
            reference_argument_overrides[node.node_id] = projected
            comparable_argument_keys[node.identity] = set(projected)
            excluded_bindings.extend(
                f"{node.identity[0]}:{node.identity[1]}:{node.identity[-1]}:{key}"
                for key in sorted(excluded)
            )
    expected_arguments = _argument_bindings(
        reference,
        {},
        common_calls,
        argument_overrides=reference_argument_overrides,
        comparable_keys=comparable_argument_keys,
        bind_map=reference_bind_map,
    )
    actual_arguments = _argument_bindings(
        candidate,
        candidate_id_map,
        common_calls,
        comparable_keys=comparable_argument_keys,
        bind_map=candidate_bind_map,
    )
    symbolic_arguments = _prf(expected_arguments, actual_arguments)
    symbolic_arguments["shared_call_count"] = len(common_calls)
    symbolic_arguments["comparison_basis"] = (
        "active_trace_public_adapter_keys_with_runtime_query_semantics"
        if public_argument_keys is not None
        else "declared_reference_arguments_with_runtime_query_semantics"
    )
    symbolic_arguments["excluded_uncomparable_count"] = len(excluded_bindings)
    symbolic_arguments["excluded_uncomparable_bindings"] = excluded_bindings
    symbolic_arguments["comparable_exact"] = symbolic_arguments["exact"]
    if excluded_bindings:
        symbolic_arguments["exact"] = None
    plan_coverage = _prf(_node_counter(reference), _node_counter(candidate))

    axes = {
        "tool_selection": tool_selection,
        "partial_order": partial_order,
        "condition_control_flow": control_flow,
        "symbolic_arguments": symbolic_arguments,
        "plan_coverage": plan_coverage,
    }
    axis_exact = [axis["exact"] for axis in axes.values()]
    exact: bool | None
    if any(value is False for value in axis_exact):
        exact = False
    elif all(value is True for value in axis_exact):
        exact = True
    else:
        exact = None
    macro_f1 = sum(float(axis["f1"]) for axis in axes.values()) / len(axes)
    return {
        "applicable": True,
        "plan_fidelity_pass": exact,
        "plan_fidelity_macro_f1": round(macro_f1, 6),
        **axes,
        # Flat fields are convenient for JSONL/leaderboard aggregation.
        "plan_tool_selection_f1": tool_selection["f1"],
        "plan_tool_selection_exact": tool_selection["exact"],
        "plan_partial_order_f1": partial_order["f1"],
        "plan_partial_order_exact": partial_order["exact"],
        "plan_condition_control_flow_f1": control_flow["f1"],
        "plan_condition_control_flow_exact": control_flow["exact"],
        "plan_symbolic_arguments_f1": symbolic_arguments["f1"],
        "plan_symbolic_arguments_exact": symbolic_arguments["exact"],
        "plan_coverage_recall": plan_coverage["recall"],
        "plan_coverage_exact": plan_coverage["exact"],
    }


def not_applicable() -> dict[str, Any]:
    """Explicit recipe-plan metric payload for ReAct/runtime-trace modes."""

    keys = (
        "plan_fidelity_pass",
        "plan_fidelity_macro_f1",
        "plan_tool_selection_f1",
        "plan_tool_selection_exact",
        "plan_partial_order_f1",
        "plan_partial_order_exact",
        "plan_condition_control_flow_f1",
        "plan_condition_control_flow_exact",
        "plan_symbolic_arguments_f1",
        "plan_symbolic_arguments_exact",
        "plan_coverage_recall",
        "plan_coverage_exact",
    )
    return {"applicable": False, **{key: None for key in keys}}


def evaluate_for_mode(
    mode: str,
    reference_plan: Any = None,
    candidate_plan: Any = None,
) -> dict[str, Any]:
    """Route global-plan versus local-trace modes without metric conflation.

    Open-loop, incremental compilation, and Replan are scored against their
    recipe-level *initial* frozen plan. ReAct is explicitly not applicable
    here; its orchestration evidence is the variant-level active trajectory
    scored elsewhere.
    """

    if mode == "react":
        return not_applicable()
    if mode not in {"plan_execute", "global_input", "replan", "incremental_workflow"}:
        raise PlanFidelityError(f"unsupported orchestration mode {mode!r}")
    if reference_plan is None or candidate_plan is None:
        raise PlanFidelityError(f"{mode} requires reference and candidate plans")
    return evaluate_plan_fidelity(reference_plan, candidate_plan)
