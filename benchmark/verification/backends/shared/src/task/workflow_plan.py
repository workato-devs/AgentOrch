"""Variant-blind symbolic WorkflowPlan protocol and deterministic resolver.

The planner predicts one complete recipe-level program.  Calls carry symbolic
arguments whose values are grounded only from public inputs, public resources,
prior outputs, loop items, caught errors, literals, or deterministic
expressions.  The same normalized program is cached and reused for every
runtime variant; no expectation, active branch, or concrete variant value is
available during planning.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Iterable


PLAN_SCHEMA = "agentorch-symbolic-workflow-plan"
PLANNER_PROMPT_VERSION = "recipe-level-symbolic-executable-plan"
INCREMENTAL_PLANNER_PROMPT = "incremental-workflow-compilation"
# GLOBAL+INPUT: the Global one-shot planner plus the concrete public runtime
# input of ONE variant (doc/global_input.md). Same schema, validator,
# decoding and prompt body; the only additions are the runtime-input section
# and the relaxation of the "never copy a runtime value" clause, which would
# otherwise contradict showing the input.
GLOBAL_INPUT_PLANNER_PROMPT = "recipe-level-symbolic-executable-plan+runtime-input"
NODE_KINDS = {
    "call", "transform", "if", "foreach", "repeat", "try", "stop", "return"
}
STRUCTURAL_RETURN_TOOLS = {
    "workato_genie.workflow_return_result",
    "workato_recipe_function.return_result",
}
VALUE_KINDS = {
    "literal", "input_ref", "output_ref", "resource_ref", "loop_ref",
    "error_ref", "expression",
}
EXPRESSION_OPS = {
    "object", "array", "interpolate", "coalesce", "get", "path_exists", "count", "length",
    "is_blank", "is_present", "eq", "ne", "gt", "gte", "lt", "lte",
    "contains", "and", "or", "not", "concat", "join", "pluck", "sort_by",
    "map", "project", "filter", "merge", "if", "lower", "upper",
    "add", "subtract", "multiply", "divide", "modulo", "negate",
    "workato_add", "workato_subtract", "workato_divide",
    "duration", "get_dynamic", "call_method", "call_function",
    "range",
    "workato_skip", "workato_clear", "workato_now", "workato_today",
    "workato_uuid",
    "ruby_or",
    "slack_text", "slack_attachments", "workato_text",
    "canonical_optional_integer", "salesforce_sobject", "schema_boolean",
}
ZERO_ARGUMENT_EXPRESSION_OPS = {
    "workato_skip", "workato_clear", "workato_now", "workato_today",
    "workato_uuid",
}
_BINDING_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class PlanValidationError(ValueError):
    """The model response is not a valid symbolic WorkflowPlan."""


class SymbolicResolutionError(RuntimeError):
    """A validated symbolic value cannot be grounded in this runtime state."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _workato_formula_text(value: Any) -> str:
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "[" + ", ".join(
            json.dumps(item, ensure_ascii=False) if isinstance(item, str)
            else _workato_formula_text(item)
            for item in value
        ) + "]"
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _workato_numeric_text(value: float | int) -> str:
    return str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)


def _arithmetic_number(value: Any) -> int | float:
    """Coerce the numeric strings accepted by Workato formula arithmetic."""

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"[+-]?\d+", text):
            return int(text)
        if re.fullmatch(r"[+-]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][+-]?\d+)?", text):
            return float(text)
    raise SymbolicResolutionError(f"formula value is not numeric: {value!r}")


def _integer_like(value: Any) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
    ) or (
        isinstance(value, str)
        and re.fullmatch(r"[+-]?\d+", value.strip()) is not None
    )


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlanValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _binding(value: Any, field_name: str) -> str:
    result = _text(value, field_name)
    if not _BINDING_RE.fullmatch(result):
        raise PlanValidationError(
            f"{field_name} must match {_BINDING_RE.pattern!r}"
        )
    return result


def _path(value: Any, field_name: str) -> list[str | int]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        return [int(item) if item.isdigit() else item for item in value.split(".") if item]
    if isinstance(value, list) and all(isinstance(item, (str, int)) for item in value):
        return list(value)
    raise PlanValidationError(f"{field_name} must be a dotted string or scalar array")


def _legacy_typed_value(value: dict[str, Any]) -> dict[str, Any] | None:
    if len(value) != 1:
        return None
    key, payload = next(iter(value.items()))
    if key == "literal":
        return {"kind": "literal", "value": payload}
    if key == "input_ref":
        return {"kind": "input_ref", "path": payload}
    if key == "resource_ref":
        return {"kind": "resource_ref", "resource": payload}
    if key in {"output_ref", "loop_ref", "error_ref"} and isinstance(payload, dict):
        binding = payload.get("binding", payload.get("bind", payload.get("node")))
        return {"kind": key, "binding": binding, "path": payload.get("path", [])}
    if key == "expression" and isinstance(payload, dict):
        return {"kind": "expression", **payload}
    return None


def _schema_path_exists(schema: dict[str, Any] | None, path: list[str | int]) -> bool:
    if not schema or not path:
        return True
    current: Any = schema
    index = 0
    while index < len(path):
        part = path[index]
        if isinstance(part, int):
            current = current.get("items") if isinstance(current, dict) else None
        elif isinstance(current, dict) and current.get("type") == "array" and part in {
            "first", "<first>", "current_item", "<current_item>"
        }:
            current = current.get("items")
        elif part in {"size", "<size>", "count", "length"}:
            # Collection pseudo-properties are runtime-derived scalar values;
            # no further schema descent is needed unless the path is malformed.
            current = {"type": "integer"}
        else:
            properties = current.get("properties") if isinstance(current, dict) else None
            if isinstance(properties, dict) and part in properties:
                current = properties[part]
            elif isinstance(properties, dict):
                # Workspace account properties are published as dotted keys
                # (for example ``Salesforce.base.url``), while the canonical
                # workflow path is segmented. Match the same longest dotted
                # key that the concrete runtime resolver accepts.
                match = next((
                    (end, ".".join(str(item) for item in path[index:end]))
                    for end in range(len(path), index + 1, -1)
                    if ".".join(str(item) for item in path[index:end]) in properties
                ), None)
                if match is None:
                    return bool(current.get("additionalProperties") is True)
                end, key = match
                current = properties[key]
                index = end - 1
            else:
                return bool(
                    isinstance(current, dict)
                    and current.get("additionalProperties") is True
                )
        if current is None:
            return False
        index += 1
    return True


def _resource_names(workspace_context: dict[str, Any] | None) -> set[str]:
    values: set[str] = set()
    context = workspace_context or {}
    cards = [
        *(context.get("workspace_resources") or []),
        *(context.get("communication_templates") or []),
    ]
    for card in cards:
        if not isinstance(card, dict):
            continue
        values.update(
            str(card[key])
            for key in ("name", "public_id", "resource_ref", "template_ref")
            if card.get(key) not in (None, "")
        )
    return values


def _literal_type_ok(value: Any, schema: dict[str, Any]) -> bool:
    expected = schema.get("type")
    if isinstance(expected, list):
        return any(_literal_type_ok(value, {**schema, "type": item}) for item in expected)
    if expected in (None, "any"):
        return True
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
        ) or (
            isinstance(value, str)
            and re.fullmatch(r"[+-]?\d+", value.strip()) is not None
        )
    if expected == "number":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
        ) or (
            isinstance(value, str)
            and re.fullmatch(
                r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", value.strip()
            )
            is not None
        )
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return True


def _normalize_value(
    value: Any,
    where: str,
    *,
    bindings: set[str],
    input_schema: dict[str, Any] | None,
    resources: set[str],
    local_bindings: set[str],
) -> dict[str, Any]:
    # Accept JSON-shaped symbolic values as deterministic shorthand.  A
    # planner will naturally write a tool array argument as ``[{...}]``, an
    # object element as ``{"field": <symbolic>, ...}``, and a scalar argument
    # as the bare JSON value (``"limit": 150``); requiring an explicit typed
    # wrapper around every container and leaf adds syntax noise without
    # testing orchestration.  Every reference and expression form in this
    # grammar is an object, so a bare scalar can only ever mean a literal —
    # the wrap does not invent any runtime value or repair semantic choices.
    if isinstance(value, list):
        value = {"kind": "expression", "op": "array", "items": value}
    if not isinstance(value, dict):
        value = {"kind": "literal", "value": value}
    legacy = _legacy_typed_value(value)
    if legacy is not None:
        value = legacy
    elif "kind" not in value:
        value = {"kind": "expression", "op": "object", "fields": value}
    if (
        value.get("kind") in EXPRESSION_OPS
        and "op" not in value
    ):
        # Common compact spelling: {"kind":"interpolate", ...}.
        value = {**value, "op": value["kind"], "kind": "expression"}
    kind = _text(value.get("kind"), f"{where}.kind")
    if kind not in VALUE_KINDS:
        raise PlanValidationError(f"{where}.kind must be one of {sorted(VALUE_KINDS)}")
    if kind == "literal":
        if "value" not in value:
            raise PlanValidationError(f"{where}.value is required")
        return {"kind": kind, "value": deepcopy(value["value"])}
    if kind == "input_ref":
        path = _path(value.get("path"), f"{where}.path")
        if not path or not _schema_path_exists(input_schema, path):
            raise PlanValidationError(f"{where} references an unknown public input path")
        return {"kind": kind, "path": path}
    if kind in {"output_ref", "loop_ref", "error_ref"}:
        bind = _binding(value.get("binding", value.get("bind")), f"{where}.binding")
        allowed = bindings | local_bindings
        if bind not in allowed:
            raise PlanValidationError(f"{where} references unknown/forward binding {bind!r}")
        return {"kind": kind, "binding": bind, "path": _path(value.get("path"), f"{where}.path")}
    if kind == "resource_ref":
        resource = _text(value.get("resource", value.get("value")), f"{where}.resource")
        if resources and resource not in resources:
            raise PlanValidationError(f"{where} references unknown public resource {resource!r}")
        return {"kind": kind, "resource": resource, "path": _path(value.get("path"), f"{where}.path")}

    op = _text(value.get("op"), f"{where}.op")
    if op not in EXPRESSION_OPS:
        raise PlanValidationError(f"{where}.op must be one of {sorted(EXPRESSION_OPS)}")
    # Accept one common JSON-schema serialization artifact: models sometimes
    # place an operation's named payload inside the single element of `args`,
    # e.g. `{"op":"object","args":[{"fields":...}]}`. This is a
    # deterministic syntactic unwrapping only; it does not invent or alter any
    # tool, binding, condition, or value.
    expression_value = dict(value)
    wrapped_args = expression_value.get("args")
    recognized = {
        "args", "items", "parts", "fields", "value", "condition",
        "item_bind", "path", "direction",
    }
    if (
        isinstance(wrapped_args, dict)
        and wrapped_args
        and "kind" not in wrapped_args
        and set(wrapped_args).issubset(recognized)
    ):
        # The same named-payload wrapper also appears directly as an object,
        # e.g. ``args:{"parts":[...]}``, rather than as a one-item array.
        # It is unambiguous and carries no orchestration decision.
        expression_value.pop("args", None)
        expression_value.update(wrapped_args)
        wrapped_args = expression_value.get("args")
    if (
        isinstance(wrapped_args, list)
        and len(wrapped_args) == 1
        and isinstance(wrapped_args[0], dict)
        and "kind" not in wrapped_args[0]
    ):
        wrapper = wrapped_args[0]
        if op == "object" and wrapper and not set(wrapper).issubset(recognized):
            expression_value.pop("args", None)
            expression_value["fields"] = wrapper
        elif wrapper and set(wrapper).issubset(recognized):
            expression_value.pop("args", None)
            expression_value.update(wrapper)
    if op in {"map", "project", "filter"} and isinstance(
        expression_value.get("items"), dict
    ):
        expression_value["args"] = [expression_value.pop("items")]
    if op == "array" and "items" not in expression_value and isinstance(
        expression_value.get("args"), list
    ):
        expression_value["items"] = expression_value.pop("args")
    if op == "interpolate" and "parts" not in expression_value and isinstance(
        expression_value.get("args"), list
    ):
        # ``args`` and ``parts`` carry the same ordered operands for string
        # interpolation. Canonicalize the accepted generic expression form so
        # validation and execution cannot disagree and resolve it as empty.
        expression_value["parts"] = expression_value.pop("args")
    if op == "object" and "fields" not in expression_value and isinstance(
        expression_value.get("args"), list
    ):
        flat_fields = expression_value.pop("args")
        if len(flat_fields) % 2:
            raise PlanValidationError(
                f"{where}.args object key/value form must have even length"
            )
        fields: dict[str, Any] = {}
        for index in range(0, len(flat_fields), 2):
            key_value = flat_fields[index]
            if not (
                isinstance(key_value, dict)
                and key_value.get("kind") == "literal"
                and isinstance(key_value.get("value"), str)
                and key_value["value"]
            ):
                raise PlanValidationError(
                    f"{where}.args[{index}] must be a literal object key"
                )
            fields[key_value["value"]] = flat_fields[index + 1]
        expression_value["fields"] = fields
    result: dict[str, Any] = {"kind": "expression", "op": op}
    expression_locals = set(local_bindings)
    if op in {"map", "project", "filter"}:
        item_bind = _binding(
            expression_value.get("item_bind"), f"{where}.item_bind"
        )
        result["item_bind"] = item_bind
        expression_locals.add(item_bind)
    for key in ("args", "items", "parts"):
        if key in expression_value:
            raw_items = expression_value[key]
            if not isinstance(raw_items, list):
                raise PlanValidationError(f"{where}.{key} must be an array")
            result[key] = [
                _normalize_value(
                    (
                        item
                        if isinstance(item, dict)
                        else {"kind": "literal", "value": item}
                    ),
                    f"{where}.{key}[{index}]", bindings=bindings,
                    input_schema=input_schema, resources=resources,
                    local_bindings=expression_locals,
                )
                for index, item in enumerate(raw_items)
            ]
    if "fields" in expression_value:
        if not isinstance(expression_value["fields"], dict):
            raise PlanValidationError(f"{where}.fields must be an object")
        result["fields"] = {
            str(key): _normalize_value(
                item, f"{where}.fields.{key}", bindings=bindings,
                input_schema=input_schema, resources=resources,
                local_bindings=expression_locals,
            )
            for key, item in expression_value["fields"].items()
        }
    if "value" in expression_value:
        result["value"] = _normalize_value(
            expression_value["value"], f"{where}.value", bindings=bindings,
            input_schema=input_schema, resources=resources,
            local_bindings=expression_locals,
        )
    if "condition" in expression_value:
        result["condition"] = _normalize_value(
            expression_value["condition"], f"{where}.condition", bindings=bindings,
            input_schema=input_schema, resources=resources,
            local_bindings=expression_locals,
        )
    if op == "if" and "condition" not in result and len(result.get("args") or []) == 3:
        # Accept the conventional if(condition, then, else) spelling and
        # canonicalize it to the executor's explicit condition + two choices.
        result["condition"] = result["args"][0]
        result["args"] = result["args"][1:]
    if "path" in expression_value:
        result["path"] = _path(expression_value["path"], f"{where}.path")
    if "direction" in expression_value:
        direction = _text(
            expression_value["direction"], f"{where}.direction"
        ).lower()
        if direction not in {"asc", "desc"}:
            raise PlanValidationError(f"{where}.direction must be asc or desc")
        result["direction"] = direction
    if (
        op not in ZERO_ARGUMENT_EXPRESSION_OPS
        and not any(
            key in result
            for key in ("args", "items", "parts", "fields", "value", "condition")
        )
    ):
        raise PlanValidationError(f"{where} expression has no operands")
    return result


def _tool_schema(tool_specs: list[dict[str, Any]] | None, tool: str) -> dict[str, Any]:
    for spec in tool_specs or []:
        if isinstance(spec, dict) and spec.get("name") == tool:
            schema = spec.get("input_schema")
            return schema if isinstance(schema, dict) else {}
    return {}


def _validate_call_schema(
    tool: str,
    arguments: dict[str, dict[str, Any]],
    tool_specs: list[dict[str, Any]] | None,
    where: str,
) -> None:
    schema = _tool_schema(tool_specs, tool)
    required = schema.get("required") or []
    missing = [str(key) for key in required if key not in arguments]
    if missing:
        raise PlanValidationError(f"{where}.arguments misses required keys {missing}")
    properties = schema.get("properties") or {}
    if schema.get("additionalProperties") is False:
        unknown = sorted(set(arguments) - set(properties))
        if unknown:
            raise PlanValidationError(f"{where}.arguments has unknown keys {unknown}")
    for key, symbolic in arguments.items():
        if symbolic.get("kind") == "literal" and isinstance(properties.get(key), dict):
            if not _literal_type_ok(symbolic.get("value"), properties[key]):
                raise PlanValidationError(f"{where}.arguments.{key} literal has wrong JSON type")


def _always_stops(nodes: list[dict[str, Any]]) -> bool:
    """Whether every path through this sequence terminates before continuing."""

    for node in nodes:
        kind = node.get("kind")
        if kind in {"stop", "return"}:
            return True
        if kind == "if" and _always_stops(node.get("then") or []) and _always_stops(
            node.get("else") or []
        ):
            return True
        if kind == "try" and _always_stops(node.get("body") or []) and _always_stops(
            node.get("catch") or []
        ):
            return True
    return False


def normalize_plan(
    plan: Any,
    allowed_tools: set[str],
    *,
    id_prefix: str = "p",
    tool_specs: list[dict[str, Any]] | None = None,
    input_schema: dict[str, Any] | None = None,
    workspace_context: dict[str, Any] | None = None,
    available_bindings: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Validate, canonicalize, and assign deterministic preorder node IDs."""

    if not isinstance(plan, list) or not plan:
        raise PlanValidationError("plan must be a non-empty array")
    counter = 0
    bindings = set(str(value) for value in available_bindings)
    resources = _resource_names(workspace_context)
    declared_bindings: set[str] = set()

    def collect_declared(values: Any) -> None:
        if not isinstance(values, list):
            return
        for raw in values:
            if not isinstance(raw, dict):
                continue
            for key in ("bind", "item_bind", "error_bind"):
                value = raw.get(key)
                if isinstance(value, str) and _BINDING_RE.fullmatch(value):
                    declared_bindings.add(value)
            for region in ("then", "else", "body", "catch"):
                collect_declared(raw.get(region))

    collect_declared(plan)

    def resolvable_bindings() -> set[str]:
        # Optional outputs from a later branch or prior repeat iteration are
        # addressable by Workato datapills. If absent at runtime they resolve
        # to null; the model must use path_exists/coalesce when required.
        return bindings | declared_bindings

    def add_bind(value: Any, where: str, local_bindings: set[str]) -> str:
        bind = _binding(value, where)
        if bind in bindings or bind in local_bindings:
            raise PlanValidationError(f"{where} duplicates binding {bind!r}")
        bindings.add(bind)
        return bind

    def nodes(values: Any, where: str, local_bindings: set[str]) -> list[dict[str, Any]]:
        nonlocal counter
        if values is None:
            # An omitted or explicit-null region is the empty region: an
            # ``if`` without an ``else`` and a ``try`` without a ``catch``
            # are complete programs, so requiring a literal ``[]`` tests
            # syntax rather than orchestration.  (The top-level plan is
            # separately required to be a non-empty array.)
            values = []
        if isinstance(values, dict):
            # Single-node shorthand: a region written as one node object.
            values = [values]
        if not isinstance(values, list):
            raise PlanValidationError(f"{where} must be an array")
        normalized: list[dict[str, Any]] = []
        for index, raw in enumerate(values):
            item_where = f"{where}[{index}]"
            if not isinstance(raw, dict):
                raise PlanValidationError(f"{item_where} must be an object")
            kind = _text(raw.get("kind"), f"{item_where}.kind")
            if kind not in NODE_KINDS:
                raise PlanValidationError(f"{item_where}.kind must be one of {sorted(NODE_KINDS)}")
            counter += 1
            item: dict[str, Any] = {"id": f"{id_prefix}{counter}", "kind": kind}
            if kind == "call":
                tool = _text(raw.get("tool"), f"{item_where}.tool")
                if tool not in allowed_tools:
                    raise PlanValidationError(f"{item_where}.tool is unavailable: {tool}")
                if not isinstance(raw.get("arguments"), dict):
                    raise PlanValidationError(f"{item_where}.arguments must be an object")
                arguments = {
                    str(key): _normalize_value(
                        value, f"{item_where}.arguments.{key}", bindings=resolvable_bindings(),
                        input_schema=input_schema, resources=resources,
                        local_bindings=local_bindings,
                    )
                    for key, value in raw["arguments"].items()
                }
                _validate_call_schema(tool, arguments, tool_specs, item_where)
                if tool in STRUCTURAL_RETURN_TOOLS:
                    if set(arguments) - {"result"}:
                        raise PlanValidationError(
                            f"{item_where} structural return accepts only result"
                        )
                    # The broad catalog retains the raw Workato authoring
                    # actions as distractors. They represent recipe control,
                    # not business tool calls, in WorkflowPlanV1.
                    item = {
                        "id": item["id"],
                        "kind": "return",
                        "value": arguments.get(
                            "result", {"kind": "literal", "value": {}}
                        ),
                    }
                else:
                    item.update({"tool": tool, "arguments": arguments})
                    expansion = raw.get("call_expansion")
                    if expansion is not None:
                        if not isinstance(expansion, dict):
                            raise PlanValidationError(
                                f"{item_where}.call_expansion must be an object"
                            )
                        collection_argument = _text(
                            expansion.get("collection_argument"),
                            f"{item_where}.call_expansion.collection_argument",
                        )
                        item_argument = _text(
                            expansion.get("item_argument"),
                            f"{item_where}.call_expansion.item_argument",
                        )
                        if collection_argument not in arguments:
                            raise PlanValidationError(
                                f"{item_where}.call_expansion references missing "
                                f"argument {collection_argument!r}"
                            )
                        if item_argument in arguments:
                            raise PlanValidationError(
                                f"{item_where}.call_expansion item argument "
                                f"{item_argument!r} already exists"
                            )
                        item["call_expansion"] = {
                            "collection_argument": collection_argument,
                            "item_argument": item_argument,
                        }
                    if raw.get("purpose"):
                        item["purpose"] = _text(raw["purpose"], f"{item_where}.purpose")
                    if raw.get("bind"):
                        item["bind"] = add_bind(
                            raw["bind"], f"{item_where}.bind", local_bindings
                        )
            elif kind == "transform":
                item["expression"] = _normalize_value(
                    raw.get("expression"), f"{item_where}.expression",
                    bindings=resolvable_bindings(), input_schema=input_schema, resources=resources,
                    local_bindings=local_bindings,
                )
                item["bind"] = add_bind(
                    raw.get("bind"), f"{item_where}.bind", local_bindings
                )
            elif kind == "if":
                item["condition"] = _normalize_value(
                    raw.get("condition"), f"{item_where}.condition",
                    bindings=resolvable_bindings(), input_schema=input_schema, resources=resources,
                    local_bindings=local_bindings,
                )
                before = set(bindings)
                item["then"] = nodes(
                    raw.get("then"), f"{item_where}.then", set(local_bindings)
                )
                then_added = set(bindings) - before
                bindings.clear()
                bindings.update(before)
                item["else"] = nodes(
                    raw.get("else"), f"{item_where}.else", set(local_bindings)
                )
                else_added = set(bindings) - before
                # A binding from either branch is a valid optional output.
                # When its branch did not run the resolver yields null, which
                # enables path_exists/coalesce patterns used by real recipes.
                # Mutually exclusive branches may reuse a stable bind name.
                bindings.clear()
                bindings.update(before | then_added | else_added)
            elif kind == "foreach":
                item["items"] = _normalize_value(
                    raw.get("items"), f"{item_where}.items", bindings=resolvable_bindings(),
                    input_schema=input_schema, resources=resources,
                    local_bindings=local_bindings,
                )
                item_bind = _binding(raw.get("item_bind"), f"{item_where}.item_bind")
                if item_bind in bindings or item_bind in local_bindings:
                    raise PlanValidationError(f"{item_where}.item_bind duplicates {item_bind!r}")
                item["item_bind"] = item_bind
                if raw.get("batch_size") is not None:
                    item["batch_size"] = _normalize_value(
                        raw.get("batch_size"),
                        f"{item_where}.batch_size",
                        bindings=resolvable_bindings(),
                        input_schema=input_schema,
                        resources=resources,
                        local_bindings=local_bindings,
                    )
                before = set(bindings)
                item["body"] = nodes(
                    raw.get("body"), f"{item_where}.body", local_bindings | {item_bind}
                )
                body_added = set(bindings) - before
                # Workato exposes the most recent iteration's datapills after
                # a loop. Missing/zero-iteration outputs resolve to null.
                bindings.clear()
                bindings.update(before | body_added)
            elif kind == "repeat":
                before = set(bindings)
                item["body"] = nodes(
                    raw.get("body"), f"{item_where}.body", set(local_bindings)
                )
                item["until"] = _normalize_value(
                    raw.get("until"), f"{item_where}.until",
                    bindings=resolvable_bindings(), input_schema=input_schema,
                    resources=resources, local_bindings=local_bindings,
                )
                # The most recent iteration outputs remain available after a
                # repeat loop, matching Workato's repeat-until datapills.
                bindings.update(before)
            elif kind == "try":
                error_bind = _binding(raw.get("error_bind"), f"{item_where}.error_bind")
                if error_bind in bindings or error_bind in local_bindings:
                    raise PlanValidationError(f"{item_where}.error_bind duplicates {error_bind!r}")
                item["error_bind"] = error_bind
                before = set(bindings)
                item["body"] = nodes(
                    raw.get("body"), f"{item_where}.body", set(local_bindings)
                )
                body_added = set(bindings) - before
                bindings.clear()
                bindings.update(before)
                item["catch"] = nodes(
                    raw.get("catch"), f"{item_where}.catch", local_bindings | {error_bind}
                )
                catch_added = set(bindings) - before
                bindings.clear()
                # Both successful and recovered outputs are optional public
                # values; a non-executed side resolves to null.
                bindings.update(before | body_added | catch_added)
            elif kind == "return":
                item["value"] = _normalize_value(
                    raw.get("value"), f"{item_where}.value", bindings=resolvable_bindings(),
                    input_schema=input_schema, resources=resources,
                    local_bindings=local_bindings,
                )
            else:
                if not isinstance(raw.get("arguments"), dict):
                    raise PlanValidationError(f"{item_where}.arguments must be an object")
                item["arguments"] = {
                    str(key): _normalize_value(
                        value, f"{item_where}.arguments.{key}", bindings=resolvable_bindings(),
                        input_schema=input_schema, resources=resources,
                        local_bindings=local_bindings,
                    )
                    for key, value in raw["arguments"].items()
                }
            normalized.append(item)
        return normalized

    result = nodes(plan, "plan", set())
    # Pure routing/recipe-function workflows can legitimately return or stop
    # without invoking a connector. Their control flow is still a complete
    # executable WorkflowPlan and must remain benchmarkable.
    return result


def walk_nodes(plan: list[dict[str, Any]]):
    for node in plan:
        yield node
        for key in ({
            "if": ("then", "else"),
            "foreach": ("body",),
            "repeat": ("body",),
            "try": ("body", "catch"),
        }.get(node.get("kind"), ())):
            yield from walk_nodes(node.get(key) or [])


def plan_hash(plan: list[dict[str, Any]]) -> str:
    return stable_hash({"schema": PLAN_SCHEMA, "plan": plan})


def append_incremental_plan_node(
    draft: list[dict[str, Any]],
    parent: str,
    raw_node: dict[str, Any],
    allowed_tools: set[str],
) -> tuple[list[dict[str, Any]], str]:
    """Append one node to an immutable-prefix planning draft.

    ``parent`` is either ``root`` or ``<draft_id>.<region>``. Control-node
    child arrays are created by the benchmark so they must be populated by
    later append actions rather than smuggled in as a complete subtree.
    Full symbolic/dataflow validation remains a finish-time operation.
    """

    if not isinstance(draft, list) or any(not isinstance(item, dict) for item in draft):
        raise PlanValidationError("incremental draft must be an array of nodes")
    if not isinstance(raw_node, dict):
        raise PlanValidationError("append_node.node must be an object")
    if any(key in raw_node for key in ("id", "draft_id")):
        raise PlanValidationError("node IDs are assigned by the benchmark")
    kind = _text(raw_node.get("kind"), "append_node.node.kind")
    if kind not in NODE_KINDS:
        raise PlanValidationError(
            f"append_node.node.kind must be one of {sorted(NODE_KINDS)}"
        )

    node = deepcopy(raw_node)
    child_regions = {
        "if": ("then", "else"),
        "foreach": ("body",),
        "repeat": ("body",),
        "try": ("body", "catch"),
    }
    reserved_children = {"then", "else", "body", "catch"}
    # Models routinely emit a control-node header with empty child-region
    # placeholders ({"kind":"try","body":[]}); that carries no smuggled
    # subtree, so strip the empty regions instead of rejecting a header
    # the model cannot express any other way. Non-empty regions are still
    # the append-children-later violation.
    for region in reserved_children.intersection(node):
        if node[region] == []:
            del node[region]
    if reserved_children.intersection(node):
        raise PlanValidationError(
            "append a control-node header first, then append each child to its region"
        )
    if kind == "call":
        tool = _text(node.get("tool"), "append_node.node.tool")
        if tool not in allowed_tools:
            raise PlanValidationError(f"append_node.node.tool is unavailable: {tool}")
        if not isinstance(node.get("arguments"), dict):
            raise PlanValidationError("append_node.node.arguments must be an object")
    elif kind == "transform":
        if "expression" not in node:
            raise PlanValidationError("append_node.node.expression is required")
        _binding(node.get("bind"), "append_node.node.bind")
    elif kind == "if":
        if "condition" not in node:
            raise PlanValidationError("append_node.node.condition is required")
    elif kind == "foreach":
        if "items" not in node:
            raise PlanValidationError("append_node.node.items is required")
        _binding(node.get("item_bind"), "append_node.node.item_bind")
        if node.get("batch_size") is not None and not isinstance(
            node.get("batch_size"), dict
        ):
            raise PlanValidationError(
                "append_node.node.batch_size must be a symbolic value"
            )
    elif kind == "repeat":
        if "until" not in node:
            raise PlanValidationError("append_node.node.until is required")
    elif kind == "try":
        _binding(node.get("error_bind"), "append_node.node.error_bind")
    elif kind == "return":
        if "value" not in node:
            raise PlanValidationError("append_node.node.value is required")
    elif not isinstance(node.get("arguments"), dict):
        raise PlanValidationError("append_node.node.arguments must be an object")

    compiled = deepcopy(draft)
    indexed: dict[str, dict[str, Any]] = {}

    def index(values: list[dict[str, Any]]) -> None:
        for item in values:
            draft_id = item.get("draft_id")
            if isinstance(draft_id, str):
                indexed[draft_id] = item
            for region in child_regions.get(str(item.get("kind") or ""), ()):
                children = item.get(region)
                if isinstance(children, list):
                    index(children)

    index(compiled)
    if parent == "root":
        target = compiled
    else:
        match = re.fullmatch(r"(d[1-9][0-9]*)\.(then|else|body|catch)", parent)
        if match is None:
            raise PlanValidationError(
                "parent must be root or <draft_id>.<then|else|body|catch>"
            )
        parent_id, region = match.groups()
        container = indexed.get(parent_id)
        if container is None:
            raise PlanValidationError(f"parent references unknown draft node {parent_id!r}")
        valid_regions = child_regions.get(str(container.get("kind") or ""), ())
        if region not in valid_regions:
            raise PlanValidationError(
                f"{parent_id} has regions {list(valid_regions)}, not {region!r}"
            )
        target = container[region]

    draft_id = f"d{len(indexed) + 1}"
    node["draft_id"] = draft_id
    for region in child_regions.get(kind, ()):
        node[region] = []
    target.append(node)
    return compiled, draft_id


@dataclass
class ResolverState:
    inputs: dict[str, Any]
    workspace_resources: list[dict[str, Any]] = field(default_factory=list)
    outputs: dict[str, Any] = field(default_factory=dict)
    loops: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, Any] = field(default_factory=dict)
    workato_uuid_index: int = 0

    def bind_output(self, binding: str | None, value: Any) -> None:
        if binding:
            self.outputs[binding] = deepcopy(value)


def _lookup(value: Any, path: list[str | int], *, missing_ok: bool = False) -> Any:
    current = value
    index = 0
    while index < len(path):
        part = path[index]
        if current is None and missing_ok:
            if (
                len(path) - index >= 2
                and path[-2] in {"first", "<first>"}
                and path[-1] == "____Size"
            ):
                return 0
            return None
        # Real connector fields win over collection pseudo-properties.  Tool
        # outputs frequently expose an explicit ``count`` key; interpreting
        # that path as ``len(the whole output object)`` flips zero-result
        # branches into the success path.
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, dict) and isinstance(part, str):
            dotted_match = next(
                (
                    (end, ".".join(str(item) for item in path[index:end]))
                    for end in range(len(path), index + 1, -1)
                    if ".".join(str(item) for item in path[index:end]) in current
                ),
                None,
            )
            if dotted_match is not None:
                end, key = dotted_match
                current = current[key]
                index = end
                continue
            if missing_ok:
                return None
            raise SymbolicResolutionError(f"path component {part!r} is unavailable")
        elif isinstance(part, str) and part in {"<size>", "size", "count", "length"}:
            try:
                current = len(current)
            except TypeError as exc:
                raise SymbolicResolutionError(f"cannot take size of {type(current).__name__}") from exc
        elif isinstance(part, str) and part in {
            "first", "<first>", "current_item", "<current_item>"
        }:
            if index + 1 < len(path) and path[index + 1] == "____Size":
                if not isinstance(current, (list, tuple)):
                    raise SymbolicResolutionError(
                        "list metadata ____Size requires a collection, got "
                        f"{type(current).__name__}"
                    )
                current = len(current)
                index += 2
                continue
            current = current[0] if isinstance(current, list) and current else None
        elif isinstance(current, (list, tuple)) and isinstance(part, int):
            current = current[part] if -len(current) <= part < len(current) else None
        elif missing_ok:
            return None
        else:
            raise SymbolicResolutionError(f"path component {part!r} is unavailable")
        index += 1
    return current


def _path_exists(value: Any, path: list[str | int]) -> bool:
    """Return whether a concrete path exists, preserving explicit nulls.

    This is intentionally a structural check rather than a truthiness or
    Workato ``presence`` check. It is used for partial recipe-variable update
    results where ``{"field": null}`` must override an older field value,
    while an omitted field must fall back to the older state.
    """

    current = value
    if not path:
        return current is not None
    for raw_part in path:
        part: str | int = raw_part
        if isinstance(raw_part, str) and raw_part.lstrip("-").isdigit():
            part = int(raw_part)
        if isinstance(current, dict):
            if part not in current:
                return False
            current = current[part]
        elif isinstance(current, (list, tuple)) and isinstance(part, int):
            if not -len(current) <= part < len(current):
                return False
            current = current[part]
        else:
            return False
    return True


def _resource_value(state: ResolverState, name: str, path: list[str | int]) -> Any:
    card = next(
        (
            item for item in state.workspace_resources
            if isinstance(item, dict) and name in {
                str(item.get("name") or ""), str(item.get("public_id") or ""),
                str(item.get("resource_ref") or ""),
                str(item.get("template_ref") or ""),
            }
        ),
        None,
    )
    if card is None:
        raise SymbolicResolutionError(f"unknown public resource {name!r}")
    if card.get("template_ref"):
        content_field = str(card.get("content_field") or "")
        if not path or path == [content_field] or path == ["message"]:
            return deepcopy(card.get("exact_template"))
    if not path:
        return card.get("public_id", card.get("resource_ref", name))
    first, *rest = path
    if isinstance(first, str):
        field_card = next(
            (
                field for field in card.get("fields") or []
                if isinstance(field, dict) and first in {
                    str(field.get("label") or ""), str(field.get("name") or ""),
                    str(field.get("field_id") or ""),
                    str(field.get("argument_field_id") or ""),
                    str(field.get("output_field_id") or ""),
                }
            ),
            None,
        )
        if field_card is not None:
            field_value = field_card.get("argument_field_id", field_card.get("field_id", first))
            return _lookup(field_value, rest, missing_ok=True)
    return _lookup(card, path)


def _blank(value: Any) -> bool:
    return value is _WORKATO_SKIP or value is None or value == "" or value == [] or value == {}


def _args(expression: dict[str, Any], state: ResolverState) -> list[Any]:
    return [resolve_symbolic_value(item, state) for item in expression.get("args") or []]


def _workflow_equal(left: Any, right: Any) -> bool:
    """Equality for connector values with JSON numeric-string round trips."""

    if left == right:
        return True
    if isinstance(left, bool) or isinstance(right, bool):
        return False
    numeric_types = (int, float)
    if isinstance(left, numeric_types) and isinstance(right, str):
        try:
            return float(left) == float(right.strip())
        except ValueError:
            return False
    if isinstance(right, numeric_types) and isinstance(left, str):
        try:
            return float(right) == float(left.strip())
        except ValueError:
            return False
    return False


class _WorkatoSkip:
    pass


_WORKATO_SKIP = _WorkatoSkip()


def _workato_integer(value: Any) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    match = re.match(r"^[+-]?\d+", str(value).strip())
    return int(match.group(0)) if match else 0


def _workato_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    text = str(value or "").strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise SymbolicResolutionError(f"cannot parse Workato time {value!r}") from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _shift_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    next_month = (
        date(year + 1, 1, 1)
        if month == 12
        else date(year, month + 1, 1)
    )
    last_day = (next_month - timedelta(days=1)).day
    return value.replace(year=year, month=month, day=min(value.day, last_day))


def _workato_match(value: Any, expected: Any) -> bool:
    if isinstance(expected, dict) and "$regex" in expected:
        payload = expected["$regex"]
        pattern = payload.get("pattern", "") if isinstance(payload, dict) else str(payload)
        flags_text = payload.get("flags", "") if isinstance(payload, dict) else ""
        flags = re.IGNORECASE if "i" in flags_text else 0
        return re.search(pattern, str(value or ""), flags) is not None
    if isinstance(expected, list):
        return any(_workflow_equal(value, item) for item in expected)
    return _workflow_equal(value, expected)


def _workato_where(rows: Any, conditions: Any) -> list[Any]:
    if not isinstance(rows, list) or not isinstance(conditions, dict):
        return []
    result: list[Any] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        accepted = True
        for raw_key, expected in conditions.items():
            key = str(raw_key)
            negate = key.endswith(" !=")
            field = key[:-3] if negate else key
            matched = _workato_match(row.get(field), expected)
            if matched == negate:
                accepted = False
                break
        if accepted:
            result.append(row)
    return result


def _workato_format_map(rows: Any, template: str) -> list[str]:
    if not isinstance(rows, list):
        return []
    pattern = re.compile(r"%\{([^}]+)\}")
    return [
        pattern.sub(
            lambda match: str(row.get(match.group(1), ""))
            if isinstance(row, dict)
            else "",
            template,
        )
        for row in rows
    ]


def _slack_block_lines_resolved(block: Any) -> list[str]:
    if not isinstance(block, dict):
        return []
    lines: list[str] = []
    section = block.get("section_text")
    if section not in (None, ""):
        lines.append(str(section))
    for element in block.get("elements") or []:
        if isinstance(element, dict) and element.get("text") not in (None, ""):
            lines.append(str(element["text"]))
    objects = block.get("objects")
    if isinstance(objects, list):
        for resolved in objects:
            if not isinstance(resolved, dict):
                continue
            lines.extend(_slack_block_lines_resolved(resolved))
            for child in resolved.get("blocks") or []:
                lines.extend(_slack_block_lines_resolved(child))
    elif isinstance(objects, dict):
        children = objects.get("blocks")
        if isinstance(children, dict):
            children = [children]
        for child in children or []:
            lines.extend(_slack_block_lines_resolved(child))
    return lines


def _slack_text_resolved(raw_input: Any) -> str:
    if not isinstance(raw_input, dict):
        raise SymbolicResolutionError("slack_text requires an object")
    lines: list[str] = []
    for block in raw_input.get("blocks") or []:
        lines.extend(_slack_block_lines_resolved(block))
    top_text = raw_input.get("text")
    if top_text not in (None, ""):
        lines.append(str(top_text))
    message = raw_input.get("message")
    message = message if isinstance(message, dict) else {}
    for key in ("pretext", "title", "attachment_text", "text"):
        if message.get(key) not in (None, ""):
            lines.append(str(message[key]))
    for key in ("pretext", "title", "attachment_text"):
        if key not in message and raw_input.get(key) not in (None, ""):
            lines.append(str(raw_input[key]))
    for field in raw_input.get("attachment_fields") or []:
        if not isinstance(field, dict):
            continue
        title = field.get("title")
        value = field.get("value")
        if title not in (None, "") or value not in (None, ""):
            lines.append(f"{'' if title is None else title}: {'' if value is None else value}")
    text = "\n".join(lines)
    if not text:
        raise SymbolicResolutionError("Slack message rendered empty text")
    return re.sub(r"<anon>(.*?)</anon>", r"\1", text, flags=re.DOTALL)


def _slack_attachments_resolved(raw_input: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_input, dict):
        raise SymbolicResolutionError("slack_attachments requires an object")
    message = raw_input.get("message")
    message = message if isinstance(message, dict) else {}
    attachment: dict[str, Any] = {}
    for public_key, source_key in (
        ("color", "color"), ("pretext", "pretext"), ("title", "title"),
        ("title_link", "title_link"), ("text", "attachment_text"),
        ("footer", "footer"), ("footer_icon", "footer_icon"),
    ):
        value = message.get(source_key, raw_input.get(source_key))
        if value not in (None, ""):
            attachment[public_key] = re.sub(
                r"<anon>(.*?)</anon>", r"\1", str(value), flags=re.DOTALL
            )
    fields: list[dict[str, Any]] = []
    for field in raw_input.get("attachment_fields") or []:
        if not isinstance(field, dict):
            continue
        title = "" if field.get("title") is None else str(field.get("title"))
        value = "" if field.get("value") is None else str(field.get("value"))
        if not title and not value:
            continue
        projected: dict[str, Any] = {"title": title, "value": value}
        if "short" in field:
            projected["short"] = str(field.get("short")).strip().lower() in {
                "true", "1", "yes"
            }
        fields.append(projected)
    if fields:
        attachment["fields"] = fields
    actions = [
        {key: value for key, value in action.items() if value not in (None, "")}
        for action in raw_input.get("attachment_buttons") or []
        if isinstance(action, dict)
    ]
    actions = [action for action in actions if action]
    if actions:
        attachment["actions"] = actions
    return [attachment] if attachment else []


def _resolve_workato_method(
    method: str, receiver: Any, args: list[Any], state: ResolverState
) -> Any:
    if method == "presence":
        return None if _blank(receiver) else receiver
    if method == "present?":
        return not _blank(receiver)
    if method == "blank?":
        return _blank(receiver)
    if method == "is_true?":
        return receiver is True or str(receiver).lower() == "true"
    if method == "is_not_true?":
        return not (receiver is True or str(receiver).lower() == "true")
    if method == "to_i":
        return _workato_integer(receiver)
    if method == "to_f":
        return float(receiver or 0)
    if method == "to_s":
        return "" if receiver is None else str(receiver)
    if method == "to_json":
        return json.dumps(receiver, ensure_ascii=False, separators=(",", ":"))
    if method in {"downcase", "upcase", "capitalize", "titleize", "unicode_normalize"}:
        text = str(receiver or "")
        return {
            "downcase": text.lower,
            "upcase": text.upper,
            "capitalize": text.capitalize,
            "titleize": lambda: re.sub(
                r"[A-Za-z0-9]+",
                lambda match: match.group(0).capitalize(),
                text.replace("_", " "),
            ),
            "unicode_normalize": lambda: unicodedata.normalize("NFC", text),
        }[method]()
    if method in {"strip", "lstrip"}:
        return str(receiver or "").strip() if method == "strip" else str(receiver or "").lstrip()
    if method == "split":
        return str(receiver or "").split(str(args[0]) if args else None)
    if method == "include?":
        return bool(args) and args[0] in receiver
    if method == "starts_with?":
        return str(receiver or "").startswith(str(args[0] if args else ""))
    if method == "ends_with?":
        return str(receiver or "").endswith(str(args[0] if args else ""))
    if method == "match?":
        return bool(args) and _workato_match(receiver, args[0])
    if method == "gsub":
        if len(args) < 2:
            raise SymbolicResolutionError("gsub requires pattern and replacement")
        pattern = args[0]
        replacement_value = args[1]
        replacement = str(replacement_value)
        if isinstance(pattern, dict) and "$regex" in pattern:
            payload = pattern["$regex"]
            regex = payload.get("pattern", "") if isinstance(payload, dict) else str(payload)
            if isinstance(replacement_value, dict):
                return re.sub(
                    regex,
                    lambda match: str(replacement_value.get(match.group(0), "")),
                    str(receiver or ""),
                )
            return re.sub(regex, replacement, str(receiver or ""))
        return str(receiver or "").replace(str(pattern), replacement)
    if method == "slice":
        start = _workato_integer(args[0]) if args else 0
        if len(args) > 1:
            return receiver[start : start + _workato_integer(args[1])]
        return receiver[start]
    if method in {"length", "size"}:
        return len(receiver) if receiver is not None else 0
    if method == "keys":
        return list(receiver) if isinstance(receiver, dict) else []
    if method == "first":
        return receiver[0] if receiver else None
    if method == "last":
        return receiver[-1] if receiver else None
    if method == "pluck":
        values = list(receiver or [])
        paths = args or []
        def path_value(row: Any, path: Any) -> Any:
            parts = path if isinstance(path, list) else [path]
            return _lookup(row, parts, missing_ok=True)
        if len(paths) == 1:
            return [path_value(row, paths[0]) for row in values]
        return [[path_value(row, path) for path in paths] for row in values]
    if method == "compact":
        return [item for item in (receiver or []) if item is not None]
    if method == "concat":
        if isinstance(receiver, list):
            return [*receiver, *(args[0] or [] if args else [])]
        return str(receiver or "") + str(args[0] if args else "")
    if method == "uniq":
        result: list[Any] = []
        for item in receiver or []:
            if item not in result:
                result.append(item)
        return result
    if method == "sum":
        return sum(receiver or [])
    if method == "min":
        return min(receiver or [], default=None)
    if method == "max":
        return max(receiver or [], default=None)
    if method == "reverse":
        return receiver[::-1]
    if method in {"join", "smart_join"}:
        separator = str(args[0]) if args else ""
        return separator.join(str(item) for item in (receiver or []))
    if method == "to_csv":
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        for row in receiver or []:
            writer.writerow(row if isinstance(row, list) else [row])
        return output.getvalue()
    if method == "where":
        return _workato_where(receiver, args[0] if args else {})
    if method == "format_map":
        return _workato_format_map(receiver, str(args[0] if args else ""))
    if method in {"to_time", "to_date"}:
        value = _workato_datetime(receiver)
        return value.isoformat() if method == "to_time" else value.date().isoformat()
    if method == "utc":
        return _workato_datetime(receiver).astimezone(timezone.utc).isoformat()
    if method == "beginning_of_day":
        value = _workato_datetime(receiver)
        return value.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    if method == "ago":
        if not isinstance(receiver, dict) or "$duration" not in receiver:
            raise SymbolicResolutionError("ago requires a duration")
        amount, unit = receiver["$duration"]
        delta = timedelta(**({unit: amount} if unit in {"seconds", "minutes", "hours", "days", "weeks"} else {}))
        configured = _lookup(state.inputs, ["execution_context", "now"], missing_ok=True)
        if configured is None:
            configured = state.inputs.get("now")
        if configured in (None, ""):
            raise SymbolicResolutionError("ago requires public execution_context.now")
        base = _workato_datetime(configured)
        result = (
            _shift_months(base, -amount * (12 if unit == "years" else 1))
            if unit in {"months", "years"}
            else base - delta
        )
        return result.astimezone(timezone.utc).isoformat()
    if method == "wday":
        # Ruby Sunday=0, Python Monday=0.
        return (_workato_datetime(receiver).weekday() + 1) % 7
    if method == "yweek":
        return _workato_datetime(receiver).isocalendar().week
    if method == "strftime":
        return _workato_datetime(receiver).strftime(str(args[0] if args else ""))
    if method == "in_time_zone":
        try:
            from zoneinfo import ZoneInfo
            return _workato_datetime(receiver).astimezone(ZoneInfo(str(args[0]))).isoformat()
        except (IndexError, ValueError) as exc:
            raise SymbolicResolutionError("in_time_zone requires a public timezone") from exc
    if method == "quote":
        return "'" + str(receiver or "").replace("'", "''") + "'"
    if method == "to_currency":
        return f"{float(receiver or 0):,.2f}"
    if method == "strip_tags":
        return re.sub(r"<[^>]+>", "", str(receiver or ""))
    raise SymbolicResolutionError(f"unsupported Workato method {method!r}")


def _resolve_workato_function(name: str, args: list[Any], state: ResolverState) -> Any:
    if name != "lookup" or len(args) < 2 or not isinstance(args[-1], dict):
        raise SymbolicResolutionError(f"unsupported Workato function {name!r}")
    resource_name = str(args[0])
    conditions = args[-1]
    card = next(
        (
            item for item in state.workspace_resources
            if isinstance(item, dict) and resource_name in {
                str(item.get("name") or ""), str(item.get("public_id") or ""),
                str(item.get("resource_ref") or ""),
            }
        ),
        None,
    )
    if card is None:
        raise SymbolicResolutionError(f"lookup resource {resource_name!r} is unavailable")
    rows = card.get("rows") or card.get("entries") or card.get("configured_values") or []
    matches = _workato_where(rows, conditions)
    return matches[0] if matches else None


def resolve_symbolic_value(value: dict[str, Any], state: ResolverState) -> Any:
    kind = value.get("kind")
    if kind == "literal":
        return deepcopy(value.get("value"))
    if kind == "input_ref":
        return _lookup(state.inputs, value.get("path") or [], missing_ok=True)
    if kind == "output_ref":
        return _lookup(state.outputs.get(str(value.get("binding"))), value.get("path") or [], missing_ok=True)
    if kind == "loop_ref":
        return _lookup(state.loops.get(str(value.get("binding"))), value.get("path") or [], missing_ok=True)
    if kind == "error_ref":
        return _lookup(state.errors.get(str(value.get("binding"))), value.get("path") or [], missing_ok=True)
    if kind == "resource_ref":
        return _resource_value(state, str(value.get("resource")), value.get("path") or [])
    if kind != "expression":
        raise SymbolicResolutionError(f"unknown symbolic value kind {kind!r}")

    op = str(value.get("op"))
    if op == "object":
        result: dict[str, Any] = {}
        for key, item in (value.get("fields") or {}).items():
            resolved = resolve_symbolic_value(item, state)
            if resolved is not _WORKATO_SKIP:
                result[key] = resolved
        return result
    if op == "array":
        resolved_items = [
            resolve_symbolic_value(item, state)
            for item in value.get("items") or []
        ]
        return [item for item in resolved_items if item is not _WORKATO_SKIP]
    if op == "interpolate":
        return "".join("" if item is None else str(item) for item in (
            resolve_symbolic_value(part, state) for part in value.get("parts") or []
        ))
    if op == "if":
        choices = value.get("args") or []
        condition = value.get("condition")
        if condition is None and len(choices) == 3:
            condition, choices = choices[0], choices[1:]
        if len(choices) != 2:
            raise SymbolicResolutionError("if expression requires two result args")
        if condition is None:
            raise SymbolicResolutionError("if expression requires a condition")
        selected = choices[0] if evaluate_condition(condition, state) else choices[1]
        return resolve_symbolic_value(selected, state)

    if op in {"coalesce", "ruby_or"}:
        children = value.get("args") or []
        if not children:
            return None
        last: Any = None
        for child in children:
            last = resolve_symbolic_value(child, state)
            blank = _blank(last)
            if op == "ruby_or":
                blank = blank or last is False
            if not blank:
                return last
        return last

    args = _args(value, state)
    if op == "get":
        return _lookup(args[0] if args else None, value.get("path") or [], missing_ok=True)
    if op == "path_exists":
        return _path_exists(args[0] if args else None, value.get("path") or [])
    if op in {"count", "length"}:
        return len(args[0]) if args and args[0] is not None else 0
    if op == "is_blank":
        return _blank(args[0] if args else None)
    if op == "is_present":
        return not _blank(args[0] if args else None)
    if op == "eq":
        return len(args) >= 2 and _workflow_equal(args[0], args[1])
    if op == "ne":
        return len(args) >= 2 and not _workflow_equal(args[0], args[1])
    if op in {"gt", "gte", "lt", "lte"}:
        if len(args) < 2:
            return False
        left, right = args[0], args[1]
        if (
            isinstance(left, str)
            and isinstance(right, (int, float))
            and not isinstance(right, bool)
        ) or (
            isinstance(right, str)
            and isinstance(left, (int, float))
            and not isinstance(left, bool)
        ):
            # Workato/Ruby formula comparisons coerce connector numeric text
            # when the opposite operand is numeric (for example "50400" > 0).
            left, right = _arithmetic_number(left), _arithmetic_number(right)
        if op == "gt":
            return left > right
        if op == "gte":
            return left >= right
        if op == "lt":
            return left < right
        return left <= right
    if op == "contains":
        return len(args) >= 2 and args[1] in args[0]
    if op == "and":
        return all(bool(item) for item in args)
    if op == "or":
        return any(bool(item) for item in args)
    if op == "not":
        return not bool(args[0] if args else None)
    if op == "concat":
        if args and all(isinstance(item, list) for item in args):
            return [child for item in args for child in item]
        return "".join("" if item is None else str(item) for item in args)
    if op == "merge":
        result: dict[str, Any] = {}
        for item in args:
            if isinstance(item, dict):
                result.update(item)
        return result
    if op == "join":
        collection = args[0] if args else []
        separator = args[1] if len(args) > 1 else ""
        return str(separator).join(str(item) for item in (collection or []))
    if op == "pluck":
        return [_lookup(item, value.get("path") or [], missing_ok=True) for item in (args[0] if args else [])]
    if op == "sort_by":
        collection = list(args[0] if args else [])
        collection.sort(
            key=lambda item: (_lookup(item, value.get("path") or [], missing_ok=True) is None,
                              _lookup(item, value.get("path") or [], missing_ok=True)),
            reverse=value.get("direction") == "desc",
        )
        return collection
    if op in {"map", "project", "filter"}:
        collection = args[0] if args else []
        if isinstance(collection, dict):
            collection = [collection]
        bind = str(value.get("item_bind"))
        previous = state.loops.get(bind, None)
        had_previous = bind in state.loops
        result = []
        try:
            for item in collection or []:
                state.loops[bind] = item
                if op == "filter":
                    if evaluate_condition(value["condition"], state):
                        result.append(item)
                else:
                    result.append(resolve_symbolic_value(value["value"], state))
        finally:
            if had_previous:
                state.loops[bind] = previous
            else:
                state.loops.pop(bind, None)
        return result
    if op == "lower":
        return str(args[0] if args else "").lower()
    if op == "upper":
        return str(args[0] if args else "").upper()
    if op == "workato_skip":
        return _WORKATO_SKIP
    if op == "workato_clear":
        return ""
    if op == "workato_now":
        configured = _lookup(state.inputs, ["execution_context", "now"], missing_ok=True)
        if configured is None:
            configured = state.inputs.get("now")
        if configured in (None, ""):
            raise SymbolicResolutionError("workato_now requires public execution_context.now")
        return str(configured)
    if op == "workato_today":
        configured = _lookup(state.inputs, ["execution_context", "today"], missing_ok=True)
        if configured is None:
            configured = state.inputs.get("today")
        if configured not in (None, ""):
            return _workato_datetime(configured).date().isoformat()
        now_value = _lookup(state.inputs, ["execution_context", "now"], missing_ok=True)
        if now_value in (None, ""):
            raise SymbolicResolutionError("workato_today requires public execution_context.today or now")
        return _workato_datetime(now_value).astimezone(timezone.utc).date().isoformat()
    if op == "workato_uuid":
        values = _lookup(
            state.inputs,
            ["execution_context", "workato_uuids"],
            missing_ok=True,
        )
        if not isinstance(values, list) or state.workato_uuid_index >= len(values):
            raise SymbolicResolutionError("workato_uuid requires a public deterministic UUID list")
        result = str(values[state.workato_uuid_index])
        state.workato_uuid_index += 1
        return result
    if op == "duration":
        if len(args) != 2:
            raise SymbolicResolutionError("duration requires value and unit")
        return {"$duration": [_workato_integer(args[0]), str(args[1])]}
    if op == "get_dynamic":
        if len(args) != 2:
            raise SymbolicResolutionError("get_dynamic requires collection and key")
        index = args[1]
        if isinstance(index, dict) and "$range" in index:
            start, end = index["$range"]
            return args[0][start : end + 1]
        return _lookup(args[0], [index], missing_ok=True)
    if op == "range":
        if len(args) not in {2, 3}:
            raise SymbolicResolutionError("range requires start, end, and optional exclusivity")
        end = _workato_integer(args[1]) - (1 if len(args) == 3 and args[2] else 0)
        return {"$range": [_workato_integer(args[0]), end]}
    if op == "canonical_optional_integer":
        if len(args) != 1:
            raise SymbolicResolutionError("canonical_optional_integer requires one operand")
        return None if _blank(args[0]) else _workato_integer(args[0])
    if op == "schema_boolean":
        if len(args) != 1:
            raise SymbolicResolutionError("schema_boolean requires one operand")
        if isinstance(args[0], str) and args[0].strip().lower() in {"true", "false"}:
            return args[0].strip().lower() == "true"
        return args[0]
    if op == "salesforce_sobject":
        if len(args) != 1:
            raise SymbolicResolutionError("salesforce_sobject requires one query")
        match = re.search(r"\bFROM\s+([A-Za-z0-9_]+)", str(args[0] or ""), flags=re.I)
        return match.group(1) if match else ""
    if op == "negate":
        return -(args[0] if args else 0)
    if op in {
        "add", "subtract", "multiply", "divide", "modulo",
        "workato_add", "workato_subtract", "workato_divide",
    }:
        if len(args) != 2:
            raise SymbolicResolutionError(f"{op} requires two operands")
        left, right = args
        if op in {"add", "subtract", "workato_add", "workato_subtract"} and isinstance(right, dict) and "$duration" in right:
            amount, unit = right["$duration"]
            left_time = _workato_datetime(left)
            direction = 1 if op in {"add", "workato_add"} else -1
            if unit in {"months", "years"}:
                result = _shift_months(
                    left_time,
                    direction * amount * (12 if unit == "years" else 1),
                )
            else:
                delta = timedelta(**{unit: amount})
                result = left_time + delta if op == "add" else left_time - delta
            return (
                result.date().isoformat()
                if isinstance(left, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", left)
                else result.isoformat()
            )
        if op == "workato_add":
            if (
                isinstance(left, str)
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}", left)
                and isinstance(right, (int, float))
                and not isinstance(right, bool)
            ):
                # Ruby Date#+ treats a numeric operand as calendar days.
                # Workato's ``to_date + 14`` must therefore remain date
                # arithmetic, not the string concatenation "YYYY-MM-DD14".
                return (
                    _workato_datetime(left) + timedelta(days=right)
                ).date().isoformat()
            if all(
                isinstance(item, (int, float)) and not isinstance(item, bool)
                for item in (left, right)
            ):
                return _workato_numeric_text(left + right)
            return _workato_formula_text(left) + _workato_formula_text(right)
        if op == "workato_subtract":
            if (
                isinstance(left, str)
                and isinstance(right, str)
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}", left)
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}", right)
            ):
                return (_workato_datetime(left) - _workato_datetime(right)).days
            try:
                return _workato_numeric_text(float(left) - float(right))
            except (TypeError, ValueError):
                difference = _workato_datetime(left) - _workato_datetime(right)
                seconds = difference.total_seconds()
                return int(seconds) if seconds.is_integer() else seconds
        if op == "workato_divide":
            return _workato_numeric_text(float(left) / float(right))
        if op == "add":
            if isinstance(left, str) and isinstance(right, (int, float)):
                try:
                    return (
                        _workato_datetime(left) + timedelta(seconds=right)
                    ).isoformat()
                except SymbolicResolutionError:
                    pass
            if isinstance(left, list) and isinstance(right, list):
                return [*left, *right]
            if (
                isinstance(left, str) and not _integer_like(left)
            ) or (
                isinstance(right, str) and not _integer_like(right)
            ):
                return _workato_formula_text(left) + _workato_formula_text(right)
            return _arithmetic_number(left) + _arithmetic_number(right)
        if op == "subtract":
            if isinstance(left, list) and isinstance(right, list):
                return [item for item in left if item not in right]
            if isinstance(left, str) and isinstance(right, str) and not (
                _integer_like(left) and _integer_like(right)
            ):
                difference = _workato_datetime(left) - _workato_datetime(right)
            else:
                difference = _arithmetic_number(left) - _arithmetic_number(right)
            if isinstance(difference, timedelta):
                seconds = difference.total_seconds()
                return int(seconds) if seconds.is_integer() else seconds
            return difference
        if op == "multiply":
            return _arithmetic_number(left) * _arithmetic_number(right)
        if op == "divide":
            divisor = _arithmetic_number(right)
            if divisor == 0:
                raise SymbolicResolutionError("division by zero in formula")
            dividend = _arithmetic_number(left)
            return dividend // divisor if _integer_like(left) and _integer_like(right) else dividend / divisor
        divisor = _arithmetic_number(right)
        if divisor == 0:
            raise SymbolicResolutionError("modulo by zero in formula")
        return _arithmetic_number(left) % divisor
    if op == "call_method":
        if len(args) < 2:
            raise SymbolicResolutionError("call_method requires receiver and method")
        return _resolve_workato_method(str(args[1]), args[0], args[2:], state)
    if op == "call_function":
        if not args:
            raise SymbolicResolutionError("call_function requires a function name")
        return _resolve_workato_function(str(args[0]), args[1:], state)
    if op == "workato_text":
        if len(args) != 1:
            raise SymbolicResolutionError("workato_text requires one operand")
        return _workato_formula_text(args[0])
    if op == "slack_text":
        if len(args) != 1:
            raise SymbolicResolutionError("slack_text requires one object")
        return _slack_text_resolved(args[0])
    if op == "slack_attachments":
        if len(args) != 1:
            raise SymbolicResolutionError("slack_attachments requires one object")
        return _slack_attachments_resolved(args[0])
    raise SymbolicResolutionError(f"unsupported expression op {op!r}")


def evaluate_condition(value: dict[str, Any], state: ResolverState) -> bool:
    return bool(resolve_symbolic_value(value, state))


def materialize_call_arguments(node: dict[str, Any], state: ResolverState) -> dict[str, Any]:
    if node.get("kind") != "call":
        raise SymbolicResolutionError("only call nodes have tool arguments")
    result: dict[str, Any] = {}
    for key, value in (node.get("arguments") or {}).items():
        resolved = resolve_symbolic_value(value, state)
        if resolved is not _WORKATO_SKIP:
            result[str(key)] = resolved
    return result


def expand_materialized_call_arguments(
    node: dict[str, Any], state: ResolverState
) -> list[dict[str, Any]]:
    """Materialize one call or its explicit one-item-per-call expansion."""

    arguments = materialize_call_arguments(node, state)
    expansion = node.get("call_expansion")
    if not isinstance(expansion, dict):
        return [arguments]
    collection_argument = str(expansion.get("collection_argument") or "")
    item_argument = str(expansion.get("item_argument") or "")
    items = arguments.pop(collection_argument, None)
    if not isinstance(items, (list, tuple)):
        raise SymbolicResolutionError(
            f"call expansion {node.get('id')} argument "
            f"{collection_argument!r} did not resolve to an array"
        )
    return [
        {**deepcopy(arguments), item_argument: deepcopy(item)}
        for item in items
    ]


def planner_prompts(
    *,
    objective: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    tool_specs: list[dict[str, Any]],
    workspace_context: dict[str, Any],
    incremental: bool = False,
    runtime_input: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Render one symbolic workflow-compilation request.

    Variant-blind by default (Global View / Local View). With
    ``runtime_input`` (GLOBAL+INPUT) the same request additionally carries the
    concrete public runtime input of one variant, rendered exactly like the
    first ReAct user turn (``task.prompt.runtime_input_parts``).
    """

    if incremental and runtime_input is not None:
        raise ValueError("runtime_input is only defined for the one-shot planner")
    system = """You design complete, executable automation workflows.

Create one complete recipe-level WorkflowPlan covering every behavior in the
task. Infer tool selection, causal order, every branch/loop/exception path,
symbolic dataflow, and every tool argument from the public capability
contracts. Requirements may be in arbitrary presentation order.

Follow every nested tool input schema exactly. Workspace field identifiers are
values to place in the schema's field-id slots; they are not substitutes for
the schema's object keys. Available tools and workspace resources are
candidates, not prescribed workflow steps. Select the necessary subset and
infer filters, limits, ordering, and other arguments from the business
requirements, public schemas, and data dependencies.

Never copy a concrete runtime value, assume a tool result, or invent a private
identifier. Express each argument and condition with typed symbolic values:
literal, input_ref, output_ref, resource_ref, loop_ref, error_ref, or a listed
deterministic expression. A call may bind its result; later output_ref values
refer to that bind name. Include only necessary tools. Do not include finish or
submit_answer calls. Represent a recipe-level result with a `return` control
node. The low-level `workato_genie.workflow_return_result` and
`workato_recipe_function.return_result` catalog entries are authoring-layer
forms of that control and must not be emitted as business tool calls."""
    if runtime_input is not None:
        # The Global clause forbids copying runtime values because Global
        # never sees any. GLOBAL+INPUT shows them, so the clause is narrowed
        # to what still holds: no assumed tool results, no invented private
        # identifiers, and no concrete values from anywhere but the input.
        system = system.replace(
            "Never copy a concrete runtime value, assume a tool result, or invent a private\n"
            "identifier.",
            "Never assume a tool result or invent a private identifier; the only\n"
            "concrete values you may use are those in the supplied runtime input.",
        )
    if incremental:
        system += """

Build the WorkflowPlan through the benchmark's append-only plan editor. On
each turn return exactly one editor-operation JSON object and no prose. This is
planning only: never execute a tool and never request or assume runtime input.
The accepted prefix is immutable."""
    else:
        system += " Return exactly one JSON object and no prose."

    user = f"""Design the complete symbolic WorkflowPlan for this task.

## Task
{objective}

## Public input schema
{json.dumps(input_schema, indent=2, sort_keys=True)}

## Public output schema
{json.dumps(output_schema, indent=2, sort_keys=True)}

## Public workspace context
{json.dumps(workspace_context, indent=2, sort_keys=True)}

For workspace field cards, use `argument_field_id` when constructing tool
arguments and `output_field_id` when reading tool results. These are public
adapter field paths, not private recipe identifiers. Refer to a candidate
workspace resource by its opaque `resource_ref`; `resource_kind` is descriptive
and is not a tool argument name.

## Available tool contracts
{json.dumps(tool_specs, indent=2, sort_keys=True)}

## Symbolic value shapes
{{"kind":"literal","value":<JSON>}}
{{"kind":"input_ref","path":["field"]}}
{{"kind":"output_ref","binding":"search_result","path":["records",0,"Id"]}}
{{"kind":"resource_ref","resource":"<public resource name/id>","path":[]}}
{{"kind":"loop_ref","binding":"item","path":["field"]}}
{{"kind":"error_ref","binding":"caught_error","path":["message"]}}
{{"kind":"expression","op":"<op>","args":[]}}

Expression ops: {json.dumps(sorted(EXPRESSION_OPS))}. Use `object` with fields,
`array` with items, and `interpolate` with parts. `map`, `project`, and `filter`
require item_bind plus value or condition. `sort_by`/`pluck` use path;
`sort_by` may set direction to asc or desc.

Every `input_ref.path` is relative to the root of the displayed Public input
schema. Include a `request` path component only when `request` is actually a
property at that root; never add an implicit wrapper. Public execution
metadata, when available, appears under the explicit `execution_context`
property and is referenced with an input_ref such as
`["execution_context","recipe_url"]`; it is not a caught-error field.

## Node shapes
{{"kind":"call","tool":"<tool>","arguments":{{}},"bind":"optional_result","purpose":"optional"}}
{{"kind":"transform","expression":<symbolic value>,"bind":"result"}}
{{"kind":"if","condition":<symbolic value>,"then":[],"else":[]}}
{{"kind":"foreach","items":<symbolic value>,"item_bind":"item","batch_size":<optional symbolic positive integer>,"body":[]}}
{{"kind":"repeat","body":[],"until":<symbolic value>}}
{{"kind":"try","error_bind":"caught_error","body":[],"catch":[]}}
{{"kind":"stop","arguments":{{"stop_reason":<symbolic value>,"stop_with_error":<symbolic value>}}}}
{{"kind":"return","value":<symbolic value>}}

Do not include node IDs; the benchmark assigns them."""
    if incremental:
        user += """

## Incremental plan editor
Emit exactly one of these JSON operations per turn:
{"type":"append_node","parent":"root","node":{<one node>}}
{"type":"append_node","parent":"d3.then","node":{<one node>}}
{"type":"finish_plan"}

The benchmark returns a `draft_id` such as `d3` after accepting a node. Use
`root` for top-level nodes or `<draft_id>.<region>` for a control child. Valid
regions are `then`/`else` for `if`, `body` for `foreach` or `repeat`, and
`body`/`catch` for `try`. When appending a control node, omit all child arrays; append its
children on later turns. Append exactly one node, never a nested subtree. Call
`finish_plan` only when the draft is a complete executable workflow.

CURRENT DRAFT:
{"plan":[]}"""
    else:
        if runtime_input is not None:
            from .prompt import runtime_input_parts

            user += (
                "\n\n## Concrete runtime input\n"
                + "\n\n".join(runtime_input_parts(runtime_input))
                + "\n\nGenerate one complete executable workflow for this runtime "
                "instance.\nThe workflow must be fully specified before execution.\n"
                "You will not receive tool results or execution feedback while "
                "constructing it."
            )
        user += '\nThe top-level response is exactly {"plan":[]}.'
    return system, user


@dataclass(frozen=True)
class NodeInfo:
    node_id: str
    kind: str
    order: int
    tool: str | None
    branches: tuple[tuple[str, str], ...]
    loops: tuple[str, ...]
    tries: tuple[tuple[str, str], ...]


class FrozenPlanGuard:
    """Legacy interactive guard plus symbolic node/argument access hooks."""

    def __init__(self, plan: list[dict[str, Any]], allowed_tools: set[str]) -> None:
        self.allowed_tools = set(allowed_tools)
        self.executed_counts: dict[str, int] = {}
        self.branch_choices: dict[str, str] = {}
        self.failed_tries: set[str] = set()
        self.last_node: NodeInfo | None = None
        self.executed_node_ids: list[str] = []
        self.replace_remaining(plan)

    def _index(self, plan: list[dict[str, Any]]) -> tuple[dict[str, NodeInfo], dict[str, dict[str, Any]]]:
        result: dict[str, NodeInfo] = {}
        raw_nodes: dict[str, dict[str, Any]] = {}
        order = 0

        def visit(values, branches=(), loops=(), tries=()):
            nonlocal order
            for node in values:
                order += 1
                node_id = str(node["id"])
                if node_id in result:
                    raise PlanValidationError(f"duplicate plan node id: {node_id}")
                result[node_id] = NodeInfo(
                    node_id, str(node["kind"]), order,
                    str(node.get("tool")) if node.get("tool") else None,
                    branches, loops, tries,
                )
                raw_nodes[node_id] = node
                if node["kind"] == "if":
                    visit(node.get("then") or [], branches + ((node_id, "then"),), loops, tries)
                    visit(node.get("else") or [], branches + ((node_id, "else"),), loops, tries)
                elif node["kind"] == "foreach":
                    visit(node.get("body") or [], branches, loops + (node_id,), tries)
                elif node["kind"] == "repeat":
                    visit(node.get("body") or [], branches, loops + (node_id,), tries)
                elif node["kind"] == "try":
                    visit(node.get("body") or [], branches, loops, tries + ((node_id, "body"),))
                    visit(node.get("catch") or [], branches, loops, tries + ((node_id, "catch"),))
        visit(plan)
        return result, raw_nodes

    def replace_remaining(self, plan: list[dict[str, Any]]) -> None:
        self.plan = deepcopy(plan)
        self.nodes, self.raw_nodes = self._index(self.plan)
        self.last_node = None
        self.branch_choices = {}
        self.failed_tries = set()

    def node(self, node_id: str) -> dict[str, Any]:
        try:
            return self.raw_nodes[node_id]
        except KeyError as exc:
            raise PlanValidationError(f"unknown plan node {node_id!r}") from exc

    def materialize(self, node_id: str, state: ResolverState) -> dict[str, Any]:
        return materialize_call_arguments(self.node(node_id), state)

    def validate_action(self, *, node_id: str, tool: str) -> str | None:
        info = self.nodes.get(node_id)
        if info is None:
            return f"plan node {node_id!r} is not in the frozen/current plan"
        if info.kind not in {"call", "stop"}:
            return f"plan node {node_id!r} has kind {info.kind!r}, not an executable action"
        expected_tool = info.tool if info.kind == "call" else "stop"
        if tool != expected_tool:
            return f"plan node {node_id!r} requires {expected_tool!r}, not {tool!r}"
        if tool not in self.allowed_tools and tool != "stop":
            return f"tool {tool!r} is unavailable"
        if self.executed_counts.get(node_id, 0) and not info.loops:
            return f"non-loop plan node {node_id!r} was already executed"
        for branch_id, choice in info.branches:
            selected = self.branch_choices.get(branch_id)
            if selected is not None and selected != choice:
                return f"plan branch {branch_id!r} already selected {selected!r}; cannot execute its {choice!r} branch"
        for try_id, section in info.tries:
            if section == "catch" and try_id not in self.failed_tries:
                return f"catch branch {try_id!r} requires a failed body observation"
        if self.last_node is not None and info.order < self.last_node.order:
            if not set(info.loops).intersection(self.last_node.loops):
                return f"plan node {node_id!r} reorders the frozen workflow before {self.last_node.node_id!r}"
        return None

    def record_action(self, node_id: str, *, failed: bool) -> None:
        info = self.nodes[node_id]
        for branch_id, choice in info.branches:
            self.branch_choices.setdefault(branch_id, choice)
        if failed:
            for try_id, section in info.tries:
                if section == "body":
                    self.failed_tries.add(try_id)
        self.executed_counts[node_id] = self.executed_counts.get(node_id, 0) + 1
        self.executed_node_ids.append(node_id)
        self.last_node = info
