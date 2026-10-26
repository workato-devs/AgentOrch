"""Fail-closed static fidelity checks for canonical workflow projections.

The raw recipe is the sole static ground truth.  Stage 1 and WorkflowPlanV1
are representations of that recipe, not independent sources of truth.  This
module therefore checks the two deterministic projection boundaries without
consulting a task description, runtime variant, or model output.

The WorkflowPlanV1 check intentionally does *not* call the compiler to build
an expected plan.  It reconstructs the expected source topology from Stage 1
and compares reference bindings independently.  This is important: using the
compiler on both sides would allow an argument-projection bug to certify its
own output.
"""

from __future__ import annotations

from collections import Counter
import json
import re
from typing import Any, Iterable

from .pipeline_common import action_tool, stable_json_hash
from .tool_catalog import ToolCatalog
from .workato_formula import workato_formula_references


STATIC_FIDELITY_SCHEMA_VERSION = "agentorch-static-workflow-fidelity-v1"

_DATAPILL_RE = re.compile(r"#\{_dp\('(.+?)'\)\}")
_FORMULA_DATAPILL_RE = re.compile(r"^=_dp\('(.+)'\)$")
_DATA_PATH_RE = re.compile(
    r"_\('data\.(?P<path>[^']+)'(?:\s*,\s*'(?P<kind>[^']+)')?\)"
)

_PLAN_FIELDS = ("then", "else", "body", "catch")
_MARKER_KINDS = {"else", "catch", "while_condition"}
_CALL_KINDS = {"tool", "terminal_response"}


class StaticWorkflowFidelityError(ValueError):
    """A derived workflow representation is not faithful to the raw recipe."""


def _walk_raw(
    node: Any,
    path: tuple[int, ...] = (),
) -> Iterable[tuple[tuple[int, ...], dict[str, Any]]]:
    if not isinstance(node, dict):
        return
    yield path, node
    for index, child in enumerate(node.get("block") or []):
        if isinstance(child, dict):
            yield from _walk_raw(child, path + (index,))


def _walk_stage1(nodes: Any) -> Iterable[dict[str, Any]]:
    for node in nodes if isinstance(nodes, list) else []:
        if not isinstance(node, dict):
            continue
        yield node
        yield from _walk_stage1(node.get("body"))


def _walk_plan(nodes: Any) -> Iterable[dict[str, Any]]:
    for node in nodes if isinstance(nodes, list) else []:
        if not isinstance(node, dict):
            continue
        yield node
        for field in _PLAN_FIELDS:
            yield from _walk_plan(node.get(field))


def _issue(
    code: str,
    layer: str,
    message: str,
    **evidence: Any,
) -> dict[str, Any]:
    result = {"code": code, "layer": layer, "message": message}
    result.update(evidence)
    return result


def _raw_to_stage1_issues(
    raw_recipe: dict[str, Any],
    stage1: dict[str, Any],
) -> list[dict[str, Any]]:
    layer = "raw_recipe_to_stage1"
    issues: list[dict[str, Any]] = []
    raw_rows = list(_walk_raw(raw_recipe))
    raw_by_path = {path: node for path, node in raw_rows}

    stage_rows = [
        node
        for node in stage1.get("nodes") or []
        if isinstance(node, dict)
    ]
    stage_by_path: dict[tuple[int, ...], dict[str, Any]] = {}
    node_ids: list[str] = []
    for node in stage_rows:
        raw_path = node.get("source_path")
        if not isinstance(raw_path, list) or not all(
            isinstance(item, int) for item in raw_path
        ):
            issues.append(
                _issue(
                    "STAGE1_SOURCE_PATH_INVALID",
                    layer,
                    "Stage 1 node has no valid raw-recipe source path.",
                    source_node=node.get("node_id"),
                    source_path=raw_path,
                )
            )
            continue
        path = tuple(raw_path)
        if path in stage_by_path:
            issues.append(
                _issue(
                    "STAGE1_SOURCE_PATH_DUPLICATE",
                    layer,
                    "Multiple Stage 1 nodes claim the same raw source path.",
                    source_path=list(path),
                )
            )
        stage_by_path[path] = node
        node_ids.append(str(node.get("node_id") or ""))

    if any(not node_id for node_id in node_ids) or len(node_ids) != len(
        set(node_ids)
    ):
        issues.append(
            _issue(
                "STAGE1_NODE_ID_INVALID",
                layer,
                "Stage 1 node IDs must be present and unique.",
            )
        )

    for path in sorted(raw_by_path.keys() - stage_by_path.keys()):
        issues.append(
            _issue(
                "RAW_NODE_DROPPED",
                layer,
                "A raw recipe node is absent from Stage 1.",
                source_path=list(path),
                raw_keyword=raw_by_path[path].get("keyword"),
            )
        )
    for path in sorted(stage_by_path.keys() - raw_by_path.keys()):
        issues.append(
            _issue(
                "STAGE1_NODE_WITHOUT_RAW_SOURCE",
                layer,
                "A Stage 1 node has no raw recipe source.",
                source_path=list(path),
                source_node=stage_by_path[path].get("node_id"),
            )
        )

    for path in sorted(raw_by_path.keys() & stage_by_path.keys()):
        raw = raw_by_path[path]
        node = stage_by_path[path]
        comparisons = {
            "source_keyword": (
                str(raw.get("keyword") or ""),
                str(node.get("source_keyword") or ""),
            ),
            "source_number": (raw.get("number"), node.get("source_number")),
            "source_as": (raw.get("as"), node.get("source_as")),
            "source_uuid": (raw.get("uuid"), node.get("source_uuid")),
            "arguments": (
                raw.get("input") if isinstance(raw.get("input"), dict) else {},
                node.get("arguments") or {},
            ),
            "skip": (bool(raw.get("skip")), bool(node.get("skip"))),
        }
        raw_keyword = str(raw.get("keyword") or "")
        if raw_keyword in {"trigger", "action"}:
            comparisons["tool_name"] = (
                action_tool(raw),
                str(node.get("tool_name") or ""),
            )
        if raw_keyword == "trigger":
            comparisons["trigger_predicate"] = (
                raw.get("filter") if isinstance(raw.get("filter"), dict) else None,
                node.get("trigger_predicate"),
            )
        if raw_keyword in {"if", "elsif", "while_condition"}:
            comparisons["condition"] = (
                raw.get("input") if isinstance(raw.get("input"), dict) else None,
                node.get("condition"),
            )
        for field, (expected, actual) in comparisons.items():
            if expected != actual:
                issues.append(
                    _issue(
                        "STAGE1_FIELD_MISMATCH",
                        layer,
                        f"Stage 1 changed raw field {field!r}.",
                        source_path=list(path),
                        source_node=node.get("node_id"),
                        field=field,
                        expected=expected,
                        actual=actual,
                    )
                )

    # The nested Stage 1 body is authoritative for the next projection.  Make
    # sure it is the same set of node objects advertised by ``nodes``.
    nested_rows = list(_walk_stage1([stage1.get("trigger")]))
    nested_ids = [str(node.get("node_id") or "") for node in nested_rows]
    if nested_ids != node_ids:
        issues.append(
            _issue(
                "STAGE1_BODY_INDEX_MISMATCH",
                layer,
                "Stage 1 nested control structure disagrees with its node index.",
                indexed_node_ids=node_ids,
                nested_node_ids=nested_ids,
            )
        )
    return issues


def _split_conditional(
    body: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    positive: list[dict[str, Any]] = []
    negative: list[dict[str, Any]] = []
    for child in body:
        kind = str(child.get("kind") or "")
        if kind == "else":
            negative.extend(
                item for item in child.get("body") or [] if isinstance(item, dict)
            )
        elif kind == "elsif":
            negative.append(child)
        else:
            positive.append(child)
    return positive, negative


def _expected_plan_topology(
    nodes: list[dict[str, Any]],
    catalog: ToolCatalog,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for source in nodes:
        if source.get("skip") is True:
            continue
        source_id = str(source.get("node_id") or "")
        kind = str(source.get("kind") or "")
        if kind in _MARKER_KINDS:
            continue
        body = [
            item for item in source.get("body") or [] if isinstance(item, dict)
        ]
        row: dict[str, Any] = {"source_node": source_id}
        if kind in _CALL_KINDS:
            row.update(
                {
                    "kind": "call",
                    "tool": catalog.canonical_tool(
                        str(source.get("tool_name") or ""), source
                    ),
                }
            )
        elif kind in {"if", "elsif"}:
            positive, negative = _split_conditional(body)
            row.update(
                {
                    "kind": "if",
                    "then": _expected_plan_topology(positive, catalog),
                    "else": _expected_plan_topology(negative, catalog),
                }
            )
        elif kind == "foreach":
            row.update(
                {"kind": "foreach", "body": _expected_plan_topology(body, catalog)}
            )
        elif kind == "repeat":
            row.update(
                {
                    "kind": "repeat",
                    "body": _expected_plan_topology(
                        [item for item in body if item.get("kind") != "while_condition"],
                        catalog,
                    ),
                }
            )
        elif kind == "try":
            protected = [item for item in body if item.get("kind") != "catch"]
            caught = next(
                (item for item in body if item.get("kind") == "catch"), None
            )
            row.update(
                {
                    "kind": "try",
                    "body": _expected_plan_topology(protected, catalog),
                    "catch": _expected_plan_topology(
                        [
                            item
                            for item in (
                                caught.get("body") if isinstance(caught, dict) else []
                            )
                            or []
                            if isinstance(item, dict)
                        ],
                        catalog,
                    ),
                }
            )
        elif kind == "stop":
            row["kind"] = "stop"
        elif kind == "terminal_result":
            row["kind"] = "return"
        else:
            row["kind"] = f"unsupported:{kind}"
        result.append(row)
    return result


def _actual_plan_topology(
    nodes: list[dict[str, Any]],
    private_source_mapping: dict[str, str],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for node in nodes:
        plan_id = str(node.get("id") or "")
        row: dict[str, Any] = {
            "source_node": private_source_mapping.get(plan_id),
            "kind": str(node.get("kind") or ""),
        }
        if row["kind"] == "call":
            row["tool"] = str(node.get("tool") or "")
        for field in _PLAN_FIELDS:
            if field in node:
                row[field] = _actual_plan_topology(
                    [item for item in node.get(field) or [] if isinstance(item, dict)],
                    private_source_mapping,
                )
        result.append(row)
    return result


def _decode_datapill(payload: str) -> dict[str, Any] | None:
    try:
        value = json.loads(payload.replace("\\'", "'"))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _path_parts(value: Any) -> list[str]:
    result: list[str] = []
    for item in value if isinstance(value, list) else []:
        if isinstance(item, (str, int)):
            result.append(str(item))
        elif isinstance(item, dict) and item.get("path_element_type"):
            path_type = str(item["path_element_type"])
            source_key = str(item.get("src_key") or "")
            if path_type == "join" and source_key:
                # The compiler lowers a Salesforce relationship hop from its
                # raw join marker/FK (Account__c) to the relationship field
                # exposed by connector results (Account__r). They are the
                # same source binding, not a changed argument dependency.
                result.append(
                    source_key[:-3] + "__r"
                    if source_key.endswith("__c")
                    else source_key.removesuffix("Id")
                )
            else:
                result.append(f"<{path_type}>")
    return result


def _token_key(token: dict[str, Any]) -> str:
    return json.dumps(token, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _source_reference_token(
    reference: dict[str, Any],
    source_as_to_node: dict[str, str],
    trigger_node_id: str,
    catch_as_to_try: dict[str, str],
    source_path_prefix_by_node: dict[str, list[str]],
    current_item_lines: set[str],
) -> dict[str, Any]:
    provider = str(reference.get("provider") or "")
    line = str(reference.get("line") or "")
    path = _path_parts(reference.get("path"))
    pill_type = str(reference.get("pill_type") or "")
    if pill_type == "foreach_meta" and not path and reference.get("key"):
        path = [str(reference["key"])]
    if line in current_item_lines and "first" in path:
        # Workato source maps sometimes spell the row selected by the map as
        # ``first``.  In that lexical map scope it is the current row, which
        # the executable plan represents with ``loop_ref``.
        path[path.index("first")] = "<current_item>"
    if pill_type == "job_context":
        return {"kind": "input", "path": ".".join(["execution_context", *path])}
    if pill_type in {"account_property", "project_property"}:
        name = str(reference.get("property_name") or "").strip()
        container = (
            "account_properties" if pill_type == "account_property" else "project_properties"
        )
        return {
            "kind": "input",
            "path": ".".join(
                ["execution_context", "workspace_configuration", container, name]
            ),
        }
    if provider == "catch" and line in catch_as_to_try:
        return {"kind": "error", "source_node": catch_as_to_try[line], "path": path}
    if line in source_as_to_node and source_as_to_node[line] != trigger_node_id:
        source_node = source_as_to_node[line]
        return {
            "kind": "output",
            "source_node": source_node,
            "path": [*source_path_prefix_by_node.get(source_node, []), *path],
        }
    if path:
        return {"kind": "input", "path": ".".join(path)}
    return {"kind": "unresolved_source", "provider": provider, "line": line}


def _source_reference_tokens(
    value: Any,
    source_as_to_node: dict[str, str],
    trigger_node_id: str,
    catch_as_to_try: dict[str, str],
    source_path_prefix_by_node: dict[str, list[str]],
) -> Counter[str]:
    result: Counter[str] = Counter()

    def source_mapping_lines(item: Any) -> set[str]:
        if not isinstance(item, str):
            return set()
        if item.startswith("="):
            return {
                str(reference.get("line") or "")
                for reference in workato_formula_references(item)
                if reference.get("line")
            }
        lines: set[str] = set()
        for match in _DATAPILL_RE.finditer(item):
            decoded = _decode_datapill(match.group(1))
            if decoded and decoded.get("line"):
                lines.add(str(decoded["line"]))
        return lines

    def add_reference(
        decoded: dict[str, Any], current_item_lines: set[str]
    ) -> None:
        result[
            _token_key(
                _source_reference_token(
                    decoded,
                    source_as_to_node,
                    trigger_node_id,
                    catch_as_to_try,
                    source_path_prefix_by_node,
                    current_item_lines,
                )
            )
        ] += 1

    def visit(item: Any, current_item_lines: set[str] | None = None) -> None:
        current_item_lines = current_item_lines or set()
        if isinstance(item, dict):
            source = item.get("____source")
            if source is not None:
                visit(source, current_item_lines)
                nested_lines = current_item_lines | source_mapping_lines(source)
                for key, nested in item.items():
                    if key != "____source":
                        visit(nested, nested_lines)
                return
            for nested in item.values():
                visit(nested, current_item_lines)
        elif isinstance(item, list):
            for nested in item:
                visit(nested, current_item_lines)
        elif isinstance(item, str):
            if item.startswith("="):
                for decoded in workato_formula_references(item):
                    add_reference(decoded, current_item_lines)
                return
            matches = list(_DATAPILL_RE.finditer(item))
            formula = _FORMULA_DATAPILL_RE.fullmatch(item)
            if formula and not matches:
                decoded = _decode_datapill(formula.group(1))
                if decoded is not None:
                    add_reference(decoded, current_item_lines)
            for match in matches:
                decoded = _decode_datapill(match.group(1))
                if decoded is not None:
                    add_reference(decoded, current_item_lines)
            for match in _DATA_PATH_RE.finditer(item):
                parts = match.group("path").split(".")
                if len(parts) < 2:
                    continue
                line = parts[1]
                reference = {
                    "provider": parts[0],
                    "line": line,
                    "path": parts[2:],
                    "pill_type": "output",
                }
                add_reference(reference, current_item_lines)

    visit(value)
    return result


def _plan_reference_tokens(
    value: Any,
    private_source_mapping: dict[str, str],
) -> Counter[str]:
    result: Counter[str] = Counter()

    def source_node(value: Any) -> str:
        text = str(value or "")
        return private_source_mapping.get(text, text)

    def visit(
        item: Any,
        map_bindings: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        map_bindings = map_bindings or {}
        if isinstance(item, list):
            for nested in item:
                visit(nested, map_bindings)
            return
        if not isinstance(item, dict):
            return
        expression = item.get("expression")
        if isinstance(expression, dict) and expression.get("op") == "salesforce_sobject":
            # Derived from the already-counted query argument solely to match
            # the connector's canonical split query/sobject call shape.
            return
        if isinstance(expression, dict) and expression.get("op") == "if":
            args = expression.get("args") or []
            fallback = args[1] if isinstance(args, list) and len(args) == 2 else None
            fallback_expression = (
                fallback.get("expression") if isinstance(fallback, dict) else None
            )
            if (
                isinstance(fallback_expression, dict)
                and fallback_expression.get("op") == "workato_skip"
            ):
                # Connector argument projection wraps a source value in a
                # presence/nil guard so the runtime can omit it.  The guard
                # deliberately repeats the same symbolic reference; it is
                # compiler machinery, not an additional source binding.
                # Count only the retained source value for lineage fidelity.
                condition = expression.get("condition")
                condition_expression = (
                    condition.get("expression")
                    if isinstance(condition, dict)
                    else None
                )
                condition_args = (
                    condition_expression.get("args") or []
                    if isinstance(condition_expression, dict)
                    else []
                )
                if (
                    isinstance(condition_expression, dict)
                    and isinstance(args, list)
                    and len(args) == 2
                    and isinstance(condition_args, list)
                    and (
                        (
                            condition_expression.get("op") == "ne"
                            and len(condition_args) == 2
                            and condition_args[0] == args[0]
                            and condition_args[1] == {"literal": None}
                        )
                        or (
                            condition_expression.get("op") == "is_present"
                            and len(condition_args) == 1
                        )
                    )
                ):
                    visit(args[0], map_bindings)
                    return
            condition = expression.get("condition")
            condition_expression = (
                condition.get("expression")
                if isinstance(condition, dict)
                else None
            )
            if (
                isinstance(condition_expression, dict)
                and condition_expression.get("op") == "ne"
                and isinstance(args, list)
                and len(args) == 2
                and fallback == {"literal": ""}
            ):
                condition_args = condition_expression.get("args") or []
                if (
                    isinstance(condition_args, list)
                    and len(condition_args) == 2
                    and condition_args[0] == args[0]
                    and condition_args[1] == {"literal": None}
                ):
                    # Connector nil-compaction repeats the retained value in
                    # both the guard and result. It still represents one raw
                    # argument binding.
                    visit(args[0], map_bindings)
                    return
            if (
                isinstance(condition_expression, dict)
                and condition_expression.get("op") == "path_exists"
                and isinstance(args, list)
                and len(args) == 2
            ):
                # Mutable Workato variables are compiled as a newest-writer
                # lookup with a declaration/older-writer fallback. The extra
                # candidate writer and path-existence probe are runtime state
                # machinery; the raw datapill is still bound to the original
                # variable line represented by the fallback.
                visit(args[1], map_bindings)
                return
        if set(item) == {"input_ref"}:
            result[_token_key({"kind": "input", "path": str(item["input_ref"])})] += 1
            return
        if set(item) == {"output_ref"} and isinstance(item["output_ref"], dict):
            ref = item["output_ref"]
            result[
                _token_key(
                    {
                        "kind": "output",
                        "source_node": source_node(ref.get("node")),
                        "path": _path_parts(ref.get("path")),
                    }
                )
            ] += 1
            return
        if set(item) == {"error_ref"} and isinstance(item["error_ref"], dict):
            ref = item["error_ref"]
            result[
                _token_key(
                    {
                        "kind": "error",
                        "source_node": source_node(ref.get("source_node")),
                        "path": _path_parts(ref.get("path")),
                    }
                )
            ] += 1
            return
        if set(item) == {"loop_ref"} and isinstance(item["loop_ref"], dict):
            ref = item["loop_ref"]
            ref_source = str(ref.get("source_node") or "")
            if ref_source in map_bindings:
                binding = map_bindings[ref_source]
                item_path = _path_parts(ref.get("path"))
                if binding.get("kind") == "output":
                    token = {
                        "kind": "output",
                        "source_node": binding["source_node"],
                        "path": [
                            *binding.get("path", []),
                            "<current_item>",
                            *item_path,
                        ],
                    }
                else:
                    token = {
                        "kind": "input",
                        "path": ".".join(
                            [
                                str(binding.get("path") or ""),
                                "<current_item>",
                                *item_path,
                            ]
                        ).strip("."),
                    }
                result[_token_key(token)] += 1
                return
            result[
                _token_key(
                    {
                        "kind": "output",
                        "source_node": source_node(ref.get("source_node")),
                        "path": _path_parts(ref.get("path")),
                    }
                )
            ] += 1
            return
        if isinstance(expression, dict) and expression.get("op") == "map":
            args = expression.get("args") or []
            source = args[0] if isinstance(args, list) and args else None
            # The map source is still one original ____source datapill and
            # must be counted.  Its item_bind is an internal serialization of
            # the raw current_item marker, not a new producer reference.
            visit(source, map_bindings)
            next_bindings = dict(map_bindings)
            binding: dict[str, Any] | None = None
            if isinstance(source, dict) and set(source) == {"output_ref"}:
                ref = source.get("output_ref")
                if isinstance(ref, dict):
                    binding = {
                        "kind": "output",
                        "source_node": source_node(ref.get("node")),
                        "path": _path_parts(ref.get("path")),
                    }
            elif isinstance(source, dict) and set(source) == {"input_ref"}:
                binding = {
                    "kind": "input",
                    "path": str(source.get("input_ref") or ""),
                }
            elif isinstance(source, dict) and set(source) == {"loop_ref"}:
                ref = source.get("loop_ref")
                if isinstance(ref, dict):
                    parent = map_bindings.get(str(ref.get("source_node") or ""))
                    item_path = _path_parts(ref.get("path"))
                    if parent and parent.get("kind") == "output":
                        binding = {
                            "kind": "output",
                            "source_node": parent["source_node"],
                            "path": [
                                *parent.get("path", []),
                                "<current_item>",
                                *item_path,
                            ],
                        }
                    elif parent and parent.get("kind") == "input":
                        binding = {
                            "kind": "input",
                            "path": ".".join(
                                [
                                    str(parent.get("path") or ""),
                                    "<current_item>",
                                    *item_path,
                                ]
                            ).strip("."),
                        }
            bind = str(expression.get("item_bind") or "")
            if bind and binding is not None:
                # Nested Workato maps commonly reuse the same source line and
                # therefore the same serialized item_bind.  The inner binding
                # shadows the outer one at execution time; mirror that lexical
                # behavior while retaining the complete producer lineage.
                next_bindings[bind] = binding
            visit(expression.get("value"), next_bindings)
            return
        if isinstance(expression, dict) and expression.get("op") == "unresolved_public_reference":
            result[
                _token_key(
                    {
                        "kind": "unresolved_plan",
                        "provider": str(expression.get("provider") or ""),
                        "line": str(expression.get("line") or ""),
                    }
                )
            ] += 1
            return
        for nested in item.values():
            visit(nested, map_bindings)

    visit(value)
    return result


def _source_binding_value(
    source: dict[str, Any],
) -> Any:
    kind = str(source.get("kind") or "")
    if kind in _CALL_KINDS or kind in {"stop", "terminal_result"}:
        return source.get("arguments") or {}
    if kind in {"if", "elsif"}:
        return source.get("condition") or source.get("arguments") or {}
    if kind == "foreach":
        return (source.get("arguments") or {}).get("source")
    if kind == "repeat":
        while_node = next(
            (
                item
                for item in source.get("body") or []
                if isinstance(item, dict) and item.get("kind") == "while_condition"
            ),
            None,
        )
        return (
            while_node.get("condition")
            if isinstance(while_node, dict)
            else source.get("condition")
        ) or {}
    return {}


def _active_workato_db_filter(item: Any) -> Any:
    """Select the editor suffix which the runtime adapter actually reads.

    Workato exports dormant alternatives such as ``value_integer`` beside
    the active ``value_default``.  Counting every editor slot makes a
    faithful plan appear to have dropped bindings which are never passed to
    the benchmark tool.
    """

    if not isinstance(item, dict):
        return item
    value_operator_pairs = (
        ("value", "op"),
        ("value_default", "op_default"),
        ("value_relation", "op_relation"),
        ("value_integer", "op_integer"),
        ("value_date_time", "op_date_time"),
        ("value_date", "op_date"),
    )
    value_key, operator_key = next(
        (
            (candidate_value, candidate_operator)
            for candidate_value, candidate_operator in value_operator_pairs
            if item.get(candidate_value) is not None
        ),
        (None, None),
    )
    if operator_key is None:
        operator_key = next(
            (
                candidate_operator
                for _, candidate_operator in value_operator_pairs
                if item.get(candidate_operator) not in (None, "")
            ),
            None,
        )

    return {
        "field": item.get("field_id") or item.get("field"),
        "op": item.get(operator_key) if operator_key else "eq",
        # The authoritative raw adapter always emits value, including null
        # for no-value isnull/isnotnull operators.
        "value": item.get(value_key) if value_key else None,
    }


def _slack_public_text_sources(arguments: dict[str, Any]) -> Any:
    """Return only authoring fields which contribute to public Slack text.

    Interactive block actions are Workato editor metadata and are not sent in
    ``slack.post_message`` arguments.  Source-mapped block groups are kept as
    structured input so the fidelity gate continues to expose the remaining
    map/join projection gap rather than silently waiving it.
    """

    lines: list[Any] = []

    def visit_block(block: Any) -> None:
        if not isinstance(block, dict):
            return
        if "____source" in block:
            # A source-mapped block contributes its collection cardinality as
            # well as the current-item fields rendered by its template.
            lines.append(block)
            return
        if block.get("section_text") not in (None, ""):
            lines.append(block.get("section_text"))
        for element in block.get("elements") or []:
            if isinstance(element, dict) and element.get("text") not in (None, ""):
                lines.append(element.get("text"))
        objects = block.get("objects")
        if isinstance(objects, dict):
            if "____source" in objects:
                # Preserve the whole mapping: both its collection source and
                # its current-item templates affect the eventual text.
                lines.append(objects)
                return
            children = objects.get("blocks")
            children = children if isinstance(children, list) else [children]
            for child in children:
                visit_block(child)

    for block in arguments.get("blocks") or []:
        visit_block(block)
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
    raw_fields = arguments.get("attachment_fields")
    if raw_fields:
        lines.append(raw_fields)
    return lines


def _slack_attachment_sources(arguments: dict[str, Any]) -> Any:
    result: dict[str, Any] = {}
    message = arguments.get("message")
    if isinstance(message, dict):
        result["message"] = {
            key: message[key]
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
            if (
                key == "attachment_buttons"
                and isinstance(arguments[key], dict)
                and "____source" in arguments[key]
            ):
                # The executable Slack projection intentionally ignores a
                # source-mapped button object, matching RawWorkatoRuntime.
                # Ordinary button lists are real attachment actions and must
                # remain in the dependency comparison.
                continue
            result[key] = arguments[key]
    return result


def _projected_source_binding_value(source: dict[str, Any]) -> Any:
    """Independently select recipe fields visible in canonical call args.

    This intentionally does not invoke ``canonical_tool_arguments``: the
    fidelity gate must not certify the compiler by executing the same adapter
    on both sides.  It mirrors only recipe-independent field selection and
    deterministic expansion needed for reference-lineage comparison.
    """

    value = _source_binding_value(source)
    if not isinstance(value, dict):
        return value
    tool = str(source.get("tool_name") or "")

    if tool == "workato_db_table.get_records":
        return {
            "table_id": value.get("table_id"),
            "filters": [
                _active_workato_db_filter(item)
                for item in value.get("filters") or []
            ],
            **(
                {"continuation_token": value.get("continuation_token")}
                if "continuation_token" in value
                else {}
            ),
            **(
                {"limit": value.get("limit")}
                if value.get("limit") not in (None, "", "100", 100)
                else {}
            ),
            **(
                {
                    "order_by_field_id": value.get("order_by_field_id"),
                    "order_direction": value.get("order_direction"),
                }
                if value.get("order_by_field_id") not in (None, "")
                else {}
            ),
        }
    if tool in {
        "workato_smart_list.create_list",
        "workato_smart_list.create_list_from_csv",
    }:
        # list_source populates RawWorkatoRuntime's private smart-list state;
        # it is deliberately absent from the recorded public call arguments.
        return {"list_name": value.get("list_name")}
    if tool in {
        "slack_bot.post_bot_message",
        "slack.post_message_to_channel",
    }:
        advanced = value.get("advanced")
        advanced = advanced if isinstance(advanced, dict) else {}
        projected = {
            "channel": value.get("channel"),
            "text_sources": _slack_public_text_sources(value),
            "thread_ts": advanced.get("thread_ts"),
            "ts": advanced.get("ts"),
        }
        if any(
            key in value
            for key in (
                "attachment_fields", "attachment_buttons", "pretext",
                "title", "attachment_text",
            )
        ) or isinstance(value.get("message"), dict):
            projected["attachment_sources"] = _slack_attachment_sources(value)
        return projected
    if tool == "slack_bot.post_bot_reply_v2":
        # The reply adapter submits both Block Kit and its plain-text fallback.
        # Runtime conversation identity/default flags contain no Stage 1 data
        # bindings and are deliberately outside this lineage-only comparison.
        return {
            "text_sources": _slack_public_text_sources(value),
            "blocks": value.get("blocks") or [],
        }
    if tool == "slack_bot.generate_menu_options":
        groups = value.get("option_groups")
        if isinstance(groups, list) and groups and groups != [{}]:
            # The runtime publishes both flattened options and grouped
            # options.  Each occurrence is therefore a real call-argument
            # binding, even though both originate from one recipe template.
            projected_groups: list[dict[str, Any]] = []
            flattened: list[Any] = []
            for group in groups:
                if not isinstance(group, dict):
                    continue
                options = group.get("options") or []
                mapped = {
                    "____source": group.get("label"),
                    **(
                        options[0]
                        if len(options) == 1 and isinstance(options[0], dict)
                        else {"options": options}
                    ),
                }
                projected_groups.append({"options": mapped})
                flattened.append(mapped)
            return {
                "options": flattened[0] if len(flattened) == 1 else flattened,
                "option_groups": projected_groups,
            }
        return {"options": value.get("options") or []}
    if tool == "salesforce.search_sobjects_soql_v2":
        # output_schema/offset are editor/result metadata; raw Salesforce
        # search records only the query, object, filters and optional limit.
        return {"query": value.get("query"), "limit": value.get("limit")}
    if tool == "salesforce.composite_update_sobject":
        return {
            "sobject_name": value.get("sobject_name"),
            "records": value.get("records"),
        }
    if tool == "workato_service.send_reply":
        return {
            key: value.get(key)
            for key in ("reply_type", "reply", "message")
            if key in value
        }
    return value


def _plan_binding_value(node: dict[str, Any]) -> Any:
    kind = str(node.get("kind") or "")
    field = {
        "call": "arguments",
        "if": "condition",
        "foreach": "items",
        "repeat": "until",
        "stop": "arguments",
        "return": "value",
    }.get(kind)
    return node.get(field) if field else {}


def _stage1_to_plan_issues(
    stage1: dict[str, Any],
    compilation: dict[str, Any],
    catalog: ToolCatalog,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    layer = "stage1_to_workflow_plan"
    issues: list[dict[str, Any]] = []
    workflow_plan = compilation.get("workflow_plan")
    private_mapping = compilation.get("private_source_mapping")
    if not isinstance(workflow_plan, dict):
        return (
            [_issue("WORKFLOW_PLAN_MISSING", layer, "Compilation has no WorkflowPlanV1 object.")],
            {},
            {},
        )
    if not isinstance(private_mapping, dict):
        return (
            [_issue("PRIVATE_SOURCE_MAPPING_MISSING", layer, "Compilation has no private source mapping.")],
            {},
            {},
        )
    private_mapping = {str(key): str(value) for key, value in private_mapping.items()}
    if str(workflow_plan.get("recipe_id") or "") != str(
        stage1.get("recipe_id") or ""
    ):
        issues.append(
            _issue(
                "PLAN_RECIPE_ID_MISMATCH",
                layer,
                "WorkflowPlanV1 is bound to a different recipe.",
                expected=stage1.get("recipe_id"),
                actual=workflow_plan.get("recipe_id"),
            )
        )
    if workflow_plan.get("workflow_a_hash") != stage1.get("workflow_A_hash"):
        issues.append(
            _issue(
                "PLAN_WORKFLOW_A_HASH_MISMATCH",
                layer,
                "WorkflowPlanV1 is not bound to this Stage 1 workflow.",
                expected=stage1.get("workflow_A_hash"),
                actual=workflow_plan.get("workflow_a_hash"),
            )
        )
    declared_plan_hash = workflow_plan.get("workflow_plan_hash")
    unhashed_plan = {
        key: value
        for key, value in workflow_plan.items()
        if key != "workflow_plan_hash"
    }
    computed_plan_hash = stable_json_hash(unhashed_plan)
    if declared_plan_hash != computed_plan_hash:
        issues.append(
            _issue(
                "WORKFLOW_PLAN_HASH_MISMATCH",
                layer,
                "WorkflowPlanV1 content does not match its declared hash.",
                expected=computed_plan_hash,
                actual=declared_plan_hash,
            )
        )
    declared_mapping_hash = compilation.get("private_source_mapping_hash")
    computed_mapping_hash = stable_json_hash(private_mapping)
    if declared_mapping_hash != computed_mapping_hash:
        issues.append(
            _issue(
                "PRIVATE_SOURCE_MAPPING_HASH_MISMATCH",
                layer,
                "Private source mapping content does not match its declared hash.",
                expected=computed_mapping_hash,
                actual=declared_mapping_hash,
            )
        )
    plan_nodes = list(_walk_plan(workflow_plan.get("workflow")))
    plan_ids = [str(node.get("id") or "") for node in plan_nodes]
    if any(not plan_id for plan_id in plan_ids) or len(plan_ids) != len(set(plan_ids)):
        issues.append(
            _issue(
                "PLAN_NODE_ID_INVALID",
                layer,
                "WorkflowPlanV1 node IDs must be present and unique.",
            )
        )
    if set(plan_ids) != set(private_mapping):
        issues.append(
            _issue(
                "PRIVATE_SOURCE_MAPPING_DOMAIN_MISMATCH",
                layer,
                "Private source mapping must cover exactly the plan nodes.",
                plan_node_ids=plan_ids,
                mapped_plan_node_ids=sorted(private_mapping),
            )
        )
    mapped_sources = list(private_mapping.values())
    if len(mapped_sources) != len(set(mapped_sources)):
        issues.append(
            _issue(
                "PRIVATE_SOURCE_MAPPING_NOT_INJECTIVE",
                layer,
                "Multiple plan nodes map to the same Stage 1 source node.",
            )
        )

    expected_topology = _expected_plan_topology(
        [item for item in stage1.get("body") or [] if isinstance(item, dict)],
        catalog,
    )
    actual_topology = _actual_plan_topology(
        [item for item in workflow_plan.get("workflow") or [] if isinstance(item, dict)],
        private_mapping,
    )
    if expected_topology != actual_topology:
        issues.append(
            _issue(
                "PLAN_TOPOLOGY_MISMATCH",
                layer,
                "WorkflowPlanV1 changed nodes, control structure, order, or tool identity.",
                expected=expected_topology,
                actual=actual_topology,
            )
        )

    stage1_nodes = [
        node for node in stage1.get("nodes") or [] if isinstance(node, dict)
    ]
    stage1_by_id = {
        str(node.get("node_id") or ""): node for node in stage1_nodes
    }
    trigger = stage1.get("trigger") if isinstance(stage1.get("trigger"), dict) else {}
    trigger_node_id = str(trigger.get("node_id") or "")
    source_as_to_node = {
        str(node["source_as"]): str(node.get("node_id") or "")
        for node in stage1_nodes
        if node.get("source_as")
    }
    variable_declarations: list[tuple[int, str, set[str]]] = []
    for index, node in enumerate(stage1_nodes):
        if node.get("tool_name") != "workato_variable.declare_variable":
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
        variable_declarations.append(
            (index, str(node.get("node_id") or ""), fields)
        )
    for index, node in enumerate(stage1_nodes):
        if node.get("tool_name") != "workato_variable.update_variables":
            continue
        name = (node.get("arguments") or {}).get("name")
        if not isinstance(name, str):
            continue
        for target in name.splitlines():
            parts = target.split(":")
            if len(parts) < 2:
                continue
            line, field = parts[-2].strip(), parts[-1].strip()
            if not line or line in source_as_to_node:
                continue
            candidates = [
                source_id
                for declaration_index, source_id, fields in variable_declarations
                if declaration_index < index and field in fields
            ]
            if len(candidates) == 1:
                source_as_to_node[line] = candidates[0]
    source_path_prefix_by_node = {
        str(node.get("node_id") or ""): ["records", "0"]
        for node in stage1_nodes
        if node.get("tool_name") == "salesforce.get_custom_object"
    }
    catch_as_to_try: dict[str, str] = {}
    for node in stage1_nodes:
        if node.get("kind") != "catch" or not node.get("source_as"):
            continue
        controller = next(
            (
                str(item.get("controller") or "")
                for item in reversed(node.get("path_conditions") or [])
                if isinstance(item, dict) and item.get("branch") == "exception"
            ),
            "",
        )
        if controller:
            catch_as_to_try[str(node["source_as"])] = controller

    plan_by_id = {str(node.get("id") or ""): node for node in plan_nodes}
    for plan_id, source_id in private_mapping.items():
        source = stage1_by_id.get(source_id)
        node = plan_by_id.get(plan_id)
        if source is None or node is None:
            continue
        expected_refs = _source_reference_tokens(
            _projected_source_binding_value(source),
            source_as_to_node,
            trigger_node_id,
            catch_as_to_try,
            source_path_prefix_by_node,
        )
        actual_refs = _plan_reference_tokens(
            _plan_binding_value(node), private_mapping
        )
        unresolved = [
            json.loads(key)
            for key in actual_refs
            if json.loads(key).get("kind") == "unresolved_plan"
        ]
        if expected_refs != actual_refs or unresolved:
            issues.append(
                _issue(
                    "PLAN_ARGUMENT_BINDING_MISMATCH",
                    layer,
                    "WorkflowPlanV1 changed or dropped a recipe argument binding.",
                    source_node=source_id,
                    plan_node=plan_id,
                    expected_references={
                        key: expected_refs[key] for key in sorted(expected_refs)
                    },
                    actual_references={
                        key: actual_refs[key] for key in sorted(actual_refs)
                    },
                    unresolved_references=unresolved,
                )
            )
    return issues, expected_topology, actual_topology


def static_workflow_fidelity_report(
    raw_recipe: dict[str, Any],
    stage1: dict[str, Any],
    compilation: dict[str, Any],
    catalog: ToolCatalog,
) -> dict[str, Any]:
    """Return a deterministic, machine-readable static fidelity report.

    ``compilation`` is the private result of ``compile_workflow_plan`` and
    must include both ``workflow_plan`` and ``private_source_mapping``.
    A caller should fail the pipeline when ``passed`` is false.
    """

    raw_issues = _raw_to_stage1_issues(raw_recipe, stage1)
    plan_issues, expected_topology, actual_topology = _stage1_to_plan_issues(
        stage1, compilation, catalog
    )
    workflow_plan = compilation.get("workflow_plan") or {}
    report: dict[str, Any] = {
        "schema_version": STATIC_FIDELITY_SCHEMA_VERSION,
        "recipe_id": str(stage1.get("recipe_id") or ""),
        "source_recipe_hash": stage1.get("source_recipe_hash"),
        "workflow_a_hash": stage1.get("workflow_A_hash"),
        "workflow_plan_hash": workflow_plan.get("workflow_plan_hash"),
        "raw_recipe_to_stage1": {
            "passed": not raw_issues,
            "raw_node_count": len(list(_walk_raw(raw_recipe))),
            "stage1_node_count": len(stage1.get("nodes") or []),
            "issues": raw_issues,
        },
        "stage1_to_workflow_plan": {
            "passed": not plan_issues,
            "stage1_projected_node_count": len(
                [item for item in _walk_plan(expected_topology)]
            ),
            "workflow_plan_node_count": len(
                list(_walk_plan(workflow_plan.get("workflow")))
            ),
            "expected_source_topology_hash": stable_json_hash(expected_topology),
            "actual_source_topology_hash": stable_json_hash(actual_topology),
            "issues": plan_issues,
        },
    }
    report["passed"] = not raw_issues and not plan_issues
    report["issue_count"] = len(raw_issues) + len(plan_issues)
    report["report_hash"] = stable_json_hash(report)
    return report


def assert_static_workflow_fidelity(
    raw_recipe: dict[str, Any],
    stage1: dict[str, Any],
    compilation: dict[str, Any],
    catalog: ToolCatalog,
) -> dict[str, Any]:
    """Return the report or raise when either static projection loses fidelity."""

    report = static_workflow_fidelity_report(
        raw_recipe, stage1, compilation, catalog
    )
    if not report["passed"]:
        codes = [
            issue["code"]
            for layer in ("raw_recipe_to_stage1", "stage1_to_workflow_plan")
            for issue in report[layer]["issues"]
        ]
        raise StaticWorkflowFidelityError(
            f"static workflow fidelity failed for {report['recipe_id']}: "
            + ", ".join(codes)
        )
    return report
