from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Iterable

from .pipeline_common import stable_json_hash
from .public_execution_context import canonical_public_runtime_input

Q_ONLY_SOLVER_PROTOCOL_VERSION = (
    "q-only-simulated-surface-forced-error-registry-v3"
)

VALUE_ASSERTION_KEYS = {
    "args_contains",
    "columns",
    "created",
    "created_count",
    "fields",
    "fields_contains",
    "http_status_code",
    "match_fields",
    "options_contains",
    "response_contains",
    "result_contains",
    "result_count",
    "rows",
    "table",
    "text_fragments",
    "updated_count",
}

LEGACY_STATE_ASSERTION_KEYS = {
    "final_fields_by_name",
    "final_lookup_table",
    "final_lookup_tables",
    "final_table",
    "log_messages",
    "menu_options",
    "message",
    "reply",
    "reply_type",
    "stopped",
}

READ_ONLY_TOOL_FRAGMENTS = (
    ".get_",
    ".lookup",
    ".query",
    ".read",
    ".search",
    ".select",
    ".snapshot",
)
INTERNAL_COMPUTATION_TOOLS = {
    "workato_runtime.declare_variable",
    "workato_runtime.log_message",
}

HIDDEN_LOOKUP_RE = re.compile(r"(?:^|[^A-Za-z0-9_])lookup\s*\(", re.I)
OPAQUE_SALESFORCE_ID_RE = re.compile(
    r"(?<![A-Za-z0-9])(?=[A-Za-z0-9]{0,2}\d)"
    r"[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?"
    r"(?![A-Za-z0-9])"
)
SALESFORCE_ID_VALUE_RE = re.compile(
    r"^[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?$"
)
SALESFORCE_VOLATILE_FIELDS = {
    "Id",
    "CreatedDate",
    "LastModifiedDate",
    "SystemModstamp",
    "LastViewedDate",
    "LastReferencedDate",
    "LastActivityDate",
}
FIRST_REFERENCE_RE = re.compile(
    r"data\.(?P<provider>[A-Za-z0-9_]+)\."
    r"(?P<source_as>[A-Za-z0-9_]+)\."
    r"(?P<collection>[A-Za-z0-9_]+)\.first\."
    r"(?P<field>[A-Za-z0-9_]+)"
)
RUNTIME_PLACEHOLDER_RE = re.compile(r"^\$[A-Z][A-Z0-9_]*$")


def _nested_strings(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for item in value.values():
            yield from _nested_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _nested_strings(item)
    elif isinstance(value, str):
        yield value


def _contains_subset(
    actual: Any,
    expected: Any,
    *,
    coerce_scalars: bool = False,
) -> bool:
    if expected == "__ANY__":
        return actual is not None
    if isinstance(expected, str) and RUNTIME_PLACEHOLDER_RE.fullmatch(expected):
        return actual not in (None, "")
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual
            and _contains_subset(
                actual[key],
                value,
                coerce_scalars=coerce_scalars,
            )
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False
        unused = list(range(len(actual)))
        for expected_item in expected:
            match = next(
                (
                    index
                    for index in unused
                    if _contains_subset(
                        actual[index],
                        expected_item,
                        coerce_scalars=coerce_scalars,
                    )
                ),
                None,
            )
            if match is None:
                return False
            unused.remove(match)
        return True
    if coerce_scalars:
        if isinstance(actual, bool) or isinstance(expected, bool):
            normalized_actual = str(actual).strip().lower()
            normalized_expected = str(expected).strip().lower()
            if normalized_actual in {"true", "false"}:
                return normalized_actual == normalized_expected
        if isinstance(actual, (int, float)) and isinstance(expected, str):
            try:
                return float(actual) == float(expected)
            except ValueError:
                pass
        if isinstance(expected, (int, float)) and isinstance(actual, str):
            try:
                return float(actual) == float(expected)
            except ValueError:
                pass
    return actual == expected


def _substantive_args(value: Any) -> Any:
    """Remove empty configuration placeholders from gold call assertions."""

    if isinstance(value, dict):
        return {
            key: cleaned
            for key, item in value.items()
            if (
                (cleaned := _substantive_args(item)) not in ({}, [], "")
                and not (
                    key in {"id", "record_id_field"}
                    and cleaned is None
                )
            )
        }
    if isinstance(value, list):
        return [
            cleaned
            for item in value
            if (cleaned := _substantive_args(item)) not in ({}, [], "")
        ]
    return value


def _contains_args_subset(actual: Any, expected: Any) -> bool:
    if not isinstance(actual, dict) or not isinstance(expected, dict):
        return _contains_subset(actual, expected, coerce_scalars=True)
    strict_keys = {"response", "reply", "body"}
    for key, value in expected.items():
        if key not in actual:
            return False
        if not _contains_subset(
            actual[key],
            value,
            coerce_scalars=key not in strict_keys,
        ):
            return False
    return True


def _normalized(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _normalized(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if key not in {"_row_id"}
        }
    if isinstance(value, list):
        return [_normalized(item) for item in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _stable_salesforce_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _stable_salesforce_fields(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
            if key not in SALESFORCE_VOLATILE_FIELDS
            and not (
                isinstance(item, str)
                and SALESFORCE_ID_VALUE_RE.fullmatch(item)
            )
        }
    if isinstance(value, list):
        return [_stable_salesforce_fields(item) for item in value]
    return value


def _salesforce_identity_fields(
    value: Any,
    *,
    nested: bool = False,
) -> Any:
    if isinstance(value, dict):
        if nested and value.get("Name") not in (None, ""):
            return {"Name": value["Name"]}
        return {
            str(key): _salesforce_identity_fields(item, nested=True)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
            if key not in SALESFORCE_VOLATILE_FIELDS
            and not (
                isinstance(item, str)
                and SALESFORCE_ID_VALUE_RE.fullmatch(item)
            )
        }
    if isinstance(value, list):
        return [
            _salesforce_identity_fields(item, nested=True)
            for item in value
        ]
    return value


def _salesforce_reference_map(
    snapshot: dict[str, Any] | None,
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    records = ((snapshot or {}).get("salesforce") or {}).get("records") or []
    for record in records:
        if not isinstance(record, dict):
            continue
        record_id = str(
            record.get("id")
            or (record.get("fields") or {}).get("Id")
            or ""
        )
        if not record_id:
            continue
        identity = {
            "sobject": str(record.get("sobject") or ""),
            "fields": _salesforce_identity_fields(
                record.get("fields") or {}
            ),
        }
        mapping[record_id] = (
            "<salesforce-record:"
            + json.dumps(identity, sort_keys=True, default=str)
            + ">"
        )
    return mapping


def _normalize_salesforce_references(
    value: Any,
    snapshot: dict[str, Any] | None,
) -> Any:
    mapping = _salesforce_reference_map(snapshot)

    def replace(item: Any) -> Any:
        if isinstance(item, dict):
            return {
                str(key): replace(child)
                for key, child in sorted(
                    item.items(),
                    key=lambda pair: str(pair[0]),
                )
            }
        if isinstance(item, list):
            return [replace(child) for child in item]
        if isinstance(item, str) and item in mapping:
            return mapping[item]
        return item

    return replace(value)


def normalized_workflow_projection(workflow_a: dict[str, Any]) -> dict[str, Any]:
    """Return a recipe-identity-free workflow projection for de-duplication.

    UI-only metadata, source UUIDs/as-ids, and timestamps are intentionally
    excluded. Configured values, expression semantics, schemas, control flow,
    terminal behavior, and action identities remain part of the fingerprint.
    """

    trigger = workflow_a.get("trigger") or {}
    source_id_map = {
        str(node.get("source_as")): str(node.get("node_id"))
        for node in workflow_a.get("nodes") or []
        if node.get("source_as") not in (None, "")
    }
    if trigger.get("source_as") not in (None, ""):
        source_id_map[str(trigger["source_as"])] = str(
            trigger.get("node_id") or "trigger"
        )

    def normalize_source_ids(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: normalize_source_ids(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [normalize_source_ids(item) for item in value]
        if isinstance(value, str):
            normalized = value
            for source_as, node_id in sorted(
                source_id_map.items(), key=lambda item: -len(item[0])
            ):
                normalized = normalized.replace(source_as, node_id)
            return normalized
        return value

    nodes = []
    for node in workflow_a.get("nodes") or []:
        nodes.append(
            {
                "node_id": node.get("node_id"),
                "kind": node.get("kind"),
                "source_keyword": node.get("source_keyword"),
                "recipe_action": node.get("recipe_action"),
                "benchmark_tool": node.get("benchmark_tool"),
                "configured_arguments": normalize_source_ids(
                    node.get("configured_arguments") or {}
                ),
                "condition": normalize_source_ids(node.get("condition")),
                "trigger_predicate": normalize_source_ids(
                    node.get("trigger_predicate")
                ),
                "formula_semantics": node.get("formula_semantics") or {},
                "input_schema": node.get("input_schema") or [],
                "output_schema": node.get("output_schema") or [],
                "path_conditions": normalize_source_ids(
                    node.get("path_conditions") or []
                ),
                "protected_by": node.get("protected_by"),
                "terminal": node.get("terminal") or {},
            }
        )
    return {
        "trigger": {
            "configured_input": normalize_source_ids(
                trigger.get("configured_input") or {}
            ),
            "predicate": normalize_source_ids(trigger.get("predicate")),
            "public_input_schema": trigger.get("public_input_schema") or {},
            "public_inputs": trigger.get("public_inputs") or [],
            "output_schema": trigger.get("output_schema") or [],
        },
        "nodes": nodes,
        "control_flow_edges": workflow_a.get("control_flow_edges") or [],
        "loop_regions": workflow_a.get("loop_regions") or [],
        "exception_regions": workflow_a.get("exception_regions") or [],
    }


def normalized_workflow_hash(workflow_a: dict[str, Any]) -> str:
    return stable_json_hash(normalized_workflow_projection(workflow_a))


def capability_closure(
    workflow_a: dict[str, Any],
    model_visible_tools: list[str],
    public_task_query: str = "",
) -> dict[str, Any]:
    """Check that Q-execution dependencies are available on the model surface.

    This is intentionally conservative. A formula lookup reads hidden runtime
    data. If no lookup capability is exposed, prose cannot make that workflow
    executable without leaking the hidden mapping.
    """

    tools = {str(tool) for tool in model_visible_tools}
    has_lookup_capability = any(
        tool.startswith(("lookup_table.", "workato_lookup."))
        for tool in tools
    )
    issues: list[dict[str, Any]] = []
    for node in workflow_a.get("nodes") or []:
        arguments = node.get("configured_arguments") or {}
        if str(node.get("benchmark_tool") or "").startswith("salesforce."):
            opaque_ids = sorted(
                {
                    match.group(0)
                    for value in _nested_strings(arguments)
                    for match in OPAQUE_SALESFORCE_ID_RE.finditer(value)
                }
            )
            unresolved_opaque_ids = [
                value
                for value in opaque_ids
                if value not in public_task_query
            ]
            if unresolved_opaque_ids:
                issues.append(
                    {
                        "issue_id": (
                            "opaque_salesforce_business_constant::"
                            f"{node.get('node_id')}"
                        ),
                        "kind": "unresolved_opaque_business_constant",
                        "node_id": node.get("node_id"),
                        "dependency": "salesforce_record_id_semantics",
                        "opaque_value_count": len(unresolved_opaque_ids),
                        "evidence": [
                            (
                                f"workflow_A.nodes.{node.get('node_id')}"
                                ".configured_arguments"
                            )
                        ],
                        "message": (
                            "A Salesforce operation depends on literal record "
                            "IDs that are neither present in the public task "
                            "query nor available through a semantic resolver."
                        ),
                    }
                )
        formula_texts = [
            value
            for value in _nested_strings(arguments)
            if value.startswith("=") or "lookup(" in value.lower()
        ]
        if (
            any(HIDDEN_LOOKUP_RE.search(value) for value in formula_texts)
            and not has_lookup_capability
        ):
            issues.append(
                {
                    "issue_id": (
                        f"hidden_lookup_dependency::{node.get('node_id')}"
                    ),
                    "kind": "missing_model_visible_capability",
                    "node_id": node.get("node_id"),
                    "dependency": "lookup_table",
                    "evidence": [
                        (
                            f"workflow_A.nodes.{node.get('node_id')}"
                            ".configured_arguments"
                        )
                    ],
                    "message": (
                        "A formula reads a hidden lookup table, but the model "
                        "surface exposes no lookup capability."
                    ),
                }
            )

    return {
        "passed": not issues,
        "model_visible_tools": sorted(tools),
        "issues": issues,
    }


def is_side_effect_tool(tool: str) -> bool:
    lowered = str(tool).lower()
    if lowered in INTERNAL_COMPUTATION_TOOLS:
        return False
    return not any(fragment in lowered for fragment in READ_ONLY_TOOL_FRAGMENTS)


def _project_observable_effect(item: dict[str, Any]) -> dict[str, Any]:
    """Remove implementation-syntax details from primary effect matching."""
    projected = dict(item)
    if isinstance(item.get("args_contains"), dict):
        args = _substantive_args(item["args_contains"])
        if str(item.get("tool") or "") == "workato_service.call_service":
            # Raw replay stores the deterministic callee reply beside the
            # invocation arguments.  On the model-visible surface that value
            # is returned by the tool; it is never an argument the solver can
            # or should supply.
            reply = args.pop("reply", None)
            if reply is not None:
                existing_result = projected.get("result_contains")
                projected["result_contains"] = {
                    **(
                        existing_result
                        if isinstance(existing_result, dict)
                        else {}
                    ),
                    "reply": reply,
                }
        if str(item.get("tool") or "") == "salesforce.search_records":
            args.pop("query", None)
            # Page/batch limits tune connector execution but do not change the
            # required business result, whose count is asserted separately.
            args.pop("limit", None)
        if str(item.get("tool") or "").startswith("snowflake."):
            # Q deliberately describes the business predicate and result, not
            # byte-exact SQL text or whether values are bound versus inlined.
            # End-state and result-count assertions cover the observable
            # behavior independently.
            args.pop("sql", None)
            args.pop("parameters", None)
        if "http_status_code" in args:
            projected["http_status_code"] = _http_status_code(
                args.pop("http_status_code")
            )
        projected["args_contains"] = args
    return projected


def _http_status_code(value: Any) -> str:
    match = re.search(r"(?<!\d)([1-5]\d{2})(?!\d)", str(value or ""))
    return match.group(1) if match else str(value or "").strip()


def _contains_symbolic_expect_reference(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            _contains_symbolic_expect_reference(item)
            for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_symbolic_expect_reference(item) for item in value)
    return (
        isinstance(value, str)
        and re.search(r"\$[A-Z][A-Z0-9_]+", value) is not None
    )


def build_observable_contract(
    variant_input: dict[str, Any],
    execution_output: dict[str, Any],
    model_visible_tools: list[str],
    *,
    include_runtime_log_effects: bool = True,
) -> dict[str, Any]:
    execution_details = execution_output.get("details") or {}
    resolved_expect = execution_details.get("expect") or {}
    current_expect = variant_input.get("expect")
    expect = (
        resolved_expect
        if (
            isinstance(resolved_expect, dict)
            and resolved_expect
            and isinstance(current_expect, dict)
            and _contains_symbolic_expect_reference(current_expect)
        )
        else (
            current_expect
            if isinstance(current_expect, dict)
            else (
                resolved_expect
                if isinstance(resolved_expect, dict)
                else {}
            )
        )
    )
    raw_execution = (
        (execution_output.get("details") or {}).get("raw_execution") or {}
    )
    raw_end_state = raw_execution.get("return_value")
    reply_expectation = expect.get("reply")
    expected_tools = {
        str(item.get("tool") or "")
        for item in expect.get("tool_expectations") or []
        if isinstance(item, dict)
    } | {str(tool) for tool in expect.get("tools") or []}
    callable_reply_surface = (
        "workato_service.call_service" in expected_tools
        or (
            not expected_tools
            and "workato_service.call_service" in model_visible_tools
            and "request" in expect
        )
    )
    if raw_end_state is None and callable_reply_surface:
        # A callable recipe's seeded reply is the result of call_service, not
        # the enclosing recipe's return value.  It is asserted on the
        # projected effect above.
        end_state = None
    elif (
        isinstance(reply_expectation, dict)
        and "reply_type" in reply_expectation
        and (
            "reply" in reply_expectation
            or "message" in reply_expectation
        )
    ):
        end_state = reply_expectation
    elif any(key in expect for key in ("reply", "reply_type", "message")):
        end_state = {
            key: expect[key]
            for key in ("reply", "reply_type", "message")
            if key in expect
        }
    else:
        end_state = raw_end_state
    end_state_present = end_state is not None
    expected_effects = [
        _project_observable_effect(item)
        for item in expect.get("tool_expectations") or []
        if isinstance(item, dict)
    ]
    legacy_tool = str(expect.get("tool") or "")
    if legacy_tool:
        legacy_effect = {
            "tool": legacy_tool,
            **{
                key: expect[key]
                for key in VALUE_ASSERTION_KEYS
                if key in expect
            },
        }
        expected_effects.append(
            _project_observable_effect(legacy_effect)
        )
    state_assertions = {
        key: expect[key]
        for key in sorted(LEGACY_STATE_ASSERTION_KEYS)
        if key in expect
    }
    if (
        expect.get("log_message") is not None
        and "log_messages" not in state_assertions
    ):
        state_assertions["log_messages"] = [expect["log_message"]]
    explicit = (
        variant_input.get("tool_expectations")
        if isinstance(variant_input.get("tool_expectations"), dict)
        else {}
    )
    required_tools = [
        str(tool)
        for tool in (
            explicit.get("required_tools")
            or expect.get("tools")
            or []
        )
    ]
    if legacy_tool and legacy_tool not in required_tools:
        required_tools.append(legacy_tool)
    gold_calls = [
        item
        for item in execution_output.get("tool_calls") or []
        if isinstance(item, dict)
    ]
    for tool in required_tools:
        if (
            not str(tool).startswith("snowflake.")
            or any(
                str(effect.get("tool") or "") == tool
                for effect in expected_effects
            )
        ):
            continue
        gold_call = next(
            (
                item
                for item in gold_calls
                if str(item.get("tool") or "") == tool
            ),
            None,
        )
        if gold_call is not None:
            expected_effects.append(
                _project_observable_effect({
                    "tool": tool,
                    "args_contains": _substantive_args(
                        gold_call.get("args") or {}
                    ),
                })
            )
    external_gold_tools = {
        str(item.get("tool") or "") for item in gold_calls
    }
    raw_trace_calls = [
        item
        for item in (
            (execution_output.get("details") or {})
            .get("raw_execution", {})
            .get("trace")
            or []
        )
        if isinstance(item, dict)
        and str(item.get("tool") or "") not in external_gold_tools
    ]
    tools_with_explicit_effects = {
        str(effect.get("tool") or "") for effect in expected_effects
    }
    effect_calls = [
        *gold_calls,
        *[
            call
            for call in raw_trace_calls
            if str(call.get("tool") or "")
            == "workato_runtime.log_message"
        ],
    ]
    for call in effect_calls:
        tool = str(call.get("tool") or "")
        if (
            tool not in model_visible_tools
            or tool in tools_with_explicit_effects
            or (
                tool == "workato_runtime.log_message"
                and not include_runtime_log_effects
            )
            or not (
                is_side_effect_tool(tool)
                or tool == "workato_runtime.log_message"
            )
        ):
            continue
        expected_effects.append(
            _project_observable_effect({
                "tool": tool,
                "args_contains": _substantive_args(
                    call.get("args") or {}
                ),
            })
        )
    forbidden_tools = [
        str(tool)
        for tool in (
            explicit.get("forbidden_tools")
            or variant_input.get("forbidden_tools")
            or []
        )
    ]
    if (
        not forbidden_tools
        and not required_tools
        and expect.get("executed_action_count") == 0
    ):
        forbidden_tools = [
            str(tool)
            for tool in model_visible_tools
            if is_side_effect_tool(str(tool))
        ]
    negative_assertions = (
        variant_input.get("negative_assertions")
        or variant_input.get("negative_side_effect_assertions")
        or []
    )
    value_effect_count = sum(
        any(key in item for key in VALUE_ASSERTION_KEYS)
        for item in expected_effects
    )
    substantive = bool(
        end_state_present
        or value_effect_count
        or state_assertions
        or forbidden_tools
        or negative_assertions
    )
    return {
        "expected_end_state_present": end_state_present,
        "expected_end_state": end_state,
        "required_effects": expected_effects,
        "state_assertions": state_assertions,
        "required_tools": list(dict.fromkeys(required_tools)),
        "forbidden_tools": list(dict.fromkeys(forbidden_tools)),
        "negative_side_effect_assertions": negative_assertions,
        "value_assertion_count": value_effect_count,
        "substantive": substantive,
        "reference_snapshot": execution_details.get("final_snapshot") or {},
        "contract_hash": stable_json_hash(
            {
                "expected_end_state_present": end_state_present,
                "expected_end_state": end_state,
                "required_effects": expected_effects,
                "state_assertions": state_assertions,
                "forbidden_tools": forbidden_tools,
                "negative_side_effect_assertions": negative_assertions,
            }
        ),
    }


def _result_count(result: Any, tool: str = "") -> int | None:
    if isinstance(result, list):
        return len(result)
    if not isinstance(result, dict):
        return None
    for key in ("count", "list_size", "totalSize"):
        value = result.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    for key in ("options", "records", "results"):
        value = result.get(key)
        if isinstance(value, list):
            return len(value)
    for value in result.values():
        if isinstance(value, list):
            return len(value)
    if (
        tool == "lookup_table.get_entry"
        and isinstance(result.get("entry"), dict)
    ):
        return 1
    return None


def _normalized_effect_field_names(value: Any) -> set[str]:
    if isinstance(value, str):
        raw_names = re.split(r"[\n,]+", value)
    elif isinstance(value, list):
        raw_names = value
    else:
        raw_names = []
    return {
        re.sub(r"[^A-Za-z0-9]", "", str(name)).casefold()
        for name in raw_names
        if str(name).strip()
    }


def _effect_match_fields_match(
    effect: dict[str, Any],
    args: dict[str, Any],
    result: dict[str, Any],
) -> bool:
    expected = _normalized_effect_field_names(effect.get("match_fields"))
    if not expected:
        return False

    payload_fields: set[str] = set()
    for key in ("record", "parameters", "fields", "columns"):
        value = args.get(key)
        if isinstance(value, dict):
            payload_fields.update(
                _normalized_effect_field_names(list(value))
            )
    for row in args.get("rows") or []:
        if isinstance(row, dict):
            payload_fields.update(
                _normalized_effect_field_names(list(row))
            )
    for row in result.get("rows") or []:
        if isinstance(row, dict):
            payload_fields.update(
                _normalized_effect_field_names(list(row))
            )
    return expected <= payload_fields


def _effect_payload_matches(
    effect: dict[str, Any],
    args: dict[str, Any],
    result: dict[str, Any],
) -> bool:
    for key in ("table",):
        if key not in effect:
            continue
        actual = args[key] if key in args else result.get(key)
        if not _contains_subset(
            actual,
            effect[key],
            coerce_scalars=True,
        ):
            return False

    for key, candidates in (
        ("rows", (args.get("rows"), result.get("rows"))),
        ("columns", (args.get("columns"), result.get("columns"))),
        (
            "fields",
            (
                args.get("fields"),
                args.get("record"),
                result.get("fields"),
                result.get("record"),
            ),
        ),
    ):
        if key in effect and not any(
            candidate is not None
            and _contains_subset(
                _canonical_state_value(
                    candidate,
                    casefold_keys=str(effect.get("tool") or "").startswith(
                        "snowflake."
                    ),
                ),
                _canonical_state_value(
                    effect[key],
                    casefold_keys=str(effect.get("tool") or "").startswith(
                        "snowflake."
                    ),
                ),
                coerce_scalars=True,
            )
            for candidate in candidates
        ):
            return False

    for expected_key, result_keys in (
        ("created", ("created",)),
        ("created_count", ("created_count", "created")),
        ("updated_count", ("updated_count", "updated")),
    ):
        if expected_key not in effect:
            continue
        actual = next(
            (result[key] for key in result_keys if key in result),
            None,
        )
        if (
            expected_key == "created"
            and actual is None
            and str(effect.get("tool") or "")
            == "salesforce.create_record"
        ):
            actual = bool(result.get("ok") and result.get("id"))
        if not _contains_subset(
            actual,
            effect[expected_key],
            coerce_scalars=True,
        ):
            return False

    if "match_fields" in effect and not _effect_match_fields_match(
        effect,
        args,
        result,
    ):
        return False
    return True


def _effect_matches(effect: dict[str, Any], call: dict[str, Any]) -> bool:
    args = call.get("args") or {}
    result = call.get("result") or {}
    if effect.get("tool") and str(call.get("tool")) != str(effect["tool"]):
        return False
    if "sobject" in effect and str(args.get("sobject") or "") != str(
        effect["sobject"]
    ):
        return False
    if "args_contains" in effect and not _contains_args_subset(
        args, effect["args_contains"]
    ):
        return False
    if not _effect_payload_matches(effect, args, result):
        return False
    if "fields_contains" in effect:
        field_candidates = [
            args.get("fields") or args.get("record") or {},
            *[
                item.get("fields") or item
                for item in args.get("records") or []
                if isinstance(item, dict)
            ],
        ]
        if not any(
            _contains_subset(fields, effect["fields_contains"])
            for fields in field_candidates
        ):
            return False
    if "options_contains" in effect:
        options = result.get("options") or args.get("options") or []
        if not _contains_subset(options, effect["options_contains"]):
            return False
    if "result_contains" in effect:
        result_candidates = [
            result,
            result.get("result"),
            result.get("response"),
        ]
        if not any(
            candidate is not None
            and _contains_subset(candidate, effect["result_contains"])
            for candidate in result_candidates
        ):
            return False
    if "response_contains" in effect and not _contains_subset(
        result.get("response", result), effect["response_contains"]
    ):
        return False
    if "result_count" in effect and _result_count(
        result,
        str(effect.get("tool") or ""),
    ) != int(
        effect["result_count"]
    ):
        return False
    if "http_status_code" in effect:
        actual_status = (
            args.get("http_status_code")
            or result.get("http_status_code")
            or result.get("status")
        )
        if _http_status_code(actual_status) != _http_status_code(
            effect["http_status_code"]
        ):
            return False
    if "text_fragments" in effect:
        strings = tuple(_nested_strings(args))
        if not all(
            any(str(fragment) in value for value in strings)
            for fragment in effect.get("text_fragments") or []
        ):
            return False
    return True


_ISO_STATE_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$"
)


def _canonical_state_value(value: Any, *, casefold_keys: bool = False) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = (
                str(key).casefold() if casefold_keys else str(key)
            )
            normalized_item = _canonical_state_value(
                item,
                casefold_keys=casefold_keys,
            )
            if (
                normalized_key in result
                and result[normalized_key] != normalized_item
            ):
                result[f"{normalized_key}#case_conflict"] = normalized_item
            else:
                result[normalized_key] = normalized_item
        return result
    if isinstance(value, list):
        return [
            _canonical_state_value(item, casefold_keys=casefold_keys)
            for item in value
        ]
    if isinstance(value, str) and _ISO_STATE_DATETIME_RE.fullmatch(value):
        iso_value = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(iso_value)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed.isoformat(timespec="microseconds").rstrip("0").rstrip(".")
    return value


def _final_table_rows(
    snapshot: dict[str, Any],
    expected_table: dict[str, Any],
) -> tuple[str, str, list[Any]]:
    table_id = str(
        expected_table.get("table_id")
        or expected_table.get("table")
        or ""
    )
    backend = str(expected_table.get("backend") or "")
    if backend == "snowflake" or not table_id:
        snowflake_tables = (
            (snapshot.get("snowflake") or {}).get("tables")
            or (snapshot.get("snowflake_live") or {}).get("tables")
            or {}
        )
        if not table_id and len(snowflake_tables) == 1:
            table_id = str(next(iter(snowflake_tables)))
        if table_id in snowflake_tables:
            return "snowflake", table_id, list(
                snowflake_tables.get(table_id) or []
            )
    workato_tables = (
        (snapshot.get("workato_db_table") or {}).get("tables") or {}
    )
    if not table_id and len(workato_tables) == 1:
        table_id = str(next(iter(workato_tables)))
    return "workato_db_table", table_id, list(
        workato_tables.get(table_id) or []
    )


def compare_observable_contract(
    contract: dict[str, Any],
    trajectory: list[dict[str, Any]],
    return_value: Any,
    final_snapshot: dict[str, Any] | None = None,
    *,
    execution_stopped: bool | None = None,
) -> dict[str, Any]:
    """Compare a candidate execution to value-bearing observable assertions."""

    checks: list[dict[str, Any]] = []
    if contract.get("expected_end_state_present"):
        reference_snapshot = contract.get("reference_snapshot") or {}
        candidate_records = (
            ((final_snapshot or {}).get("salesforce") or {})
            .get("records")
            or []
        )
        reference_records = (
            (reference_snapshot.get("salesforce") or {})
            .get("records")
            or []
        )
        combined_snapshot = {
            "salesforce": {
                "records": [
                    *candidate_records,
                    *reference_records,
                ]
            }
        }
        expected_end_state = _normalize_salesforce_references(
            _normalized(contract.get("expected_end_state")),
            reference_snapshot,
        )
        actual_end_state = _normalize_salesforce_references(
            _normalized(return_value),
            combined_snapshot,
        )
        checks.append(
            {
                "check": "expected_end_state",
                "passed": _contains_subset(
                    actual_end_state,
                    expected_end_state,
                ),
                "expected": contract.get("expected_end_state"),
                "actual": return_value,
            }
        )

    for effect_index, effect in enumerate(contract.get("required_effects") or []):
        matching = next(
            (
                index
                for index, call in enumerate(trajectory)
                if _effect_matches(effect, call)
            ),
            None,
        )
        checks.append(
            {
                "check": f"required_effect_{effect_index}",
                "passed": matching is not None,
                "effect": effect,
                "matched_trace_index": matching,
            }
        )

    actual_tools = [str(call.get("tool") or "") for call in trajectory]
    for tool in contract.get("forbidden_tools") or []:
        checks.append(
            {
                "check": f"forbidden_tool::{tool}",
                "passed": str(tool) not in actual_tools,
                "tool": tool,
            }
        )

    state_assertions = contract.get("state_assertions") or {}
    snapshot = final_snapshot or {}
    if "menu_options" in state_assertions:
        actual_options = [
            option
            for call in trajectory
            if str(call.get("tool") or "") == "slack_bot.generate_menu_options"
            for option in (call.get("args") or {}).get("options") or []
        ]
        raw_expected_options = state_assertions["menu_options"]
        expected_options = (
            [
                {
                    key: value
                    for key, value in item.items()
                    if key in {"label", "value"}
                }
                for item in raw_expected_options
                if isinstance(item, dict)
            ]
            if isinstance(raw_expected_options, list)
            else []
        )
        checks.append(
            {
                "check": "menu_options",
                "passed": _contains_subset(actual_options, expected_options)
                and len(actual_options) == len(expected_options),
                "expected": expected_options,
                "actual": actual_options,
            }
        )
    if "log_messages" in state_assertions:
        actual_messages = [
            (call.get("args") or {}).get("message")
            for call in trajectory
            if str(call.get("tool") or "") == "workato_runtime.log_message"
        ]
        checks.append(
            {
                "check": "log_messages",
                "passed": actual_messages == state_assertions["log_messages"],
                "expected": state_assertions["log_messages"],
                "actual": actual_messages,
            }
        )
    if "stopped" in state_assertions and execution_stopped is not None:
        checks.append(
            {
                "check": "stopped",
                "passed": execution_stopped is bool(
                    state_assertions["stopped"]
                ),
                "expected": bool(state_assertions["stopped"]),
                "actual": execution_stopped,
            }
        )
    if "final_fields_by_name" in state_assertions:
        records = (
            (snapshot.get("salesforce") or {}).get("records") or []
        )
        actual_by_name = {
            str((record.get("fields") or {}).get("Name") or ""): (
                record.get("fields") or {}
            )
            for record in records
            if isinstance(record, dict)
        }
        expected_by_name = state_assertions["final_fields_by_name"]
        checks.append(
            {
                "check": "final_fields_by_name",
                "passed": isinstance(expected_by_name, dict)
                and all(
                    name in actual_by_name
                    and _contains_subset(actual_by_name[name], fields)
                    for name, fields in expected_by_name.items()
                ),
                "expected": expected_by_name,
                "actual": actual_by_name,
            }
        )
    if "final_table" in state_assertions:
        expected_table = state_assertions["final_table"]
        backend, table_id, rows = _final_table_rows(
            snapshot,
            expected_table,
        )
        casefold_keys = backend == "snowflake"
        row_checks = []
        for item in expected_table.get("rows") or []:
            fields = item.get("fields") or item
            match_fields = (
                item.get("match_fields")
                or expected_table.get("match_fields")
                or list(fields)
            )
            canonical_fields = _canonical_state_value(
                fields,
                casefold_keys=casefold_keys,
            )
            canonical_match_fields = [
                str(field).casefold() if casefold_keys else str(field)
                for field in match_fields
            ]
            row_checks.append(
                any(
                    isinstance(row, dict)
                    and all(
                        _contains_subset(
                            canonical_row.get(field),
                            canonical_fields.get(field),
                            coerce_scalars=True,
                        )
                        for field in canonical_match_fields
                    )
                    and _contains_subset(
                        canonical_row,
                        canonical_fields,
                        coerce_scalars=True,
                    )
                    for row in rows
                    for canonical_row in [
                        _canonical_state_value(
                            row,
                            casefold_keys=casefold_keys,
                        )
                    ]
                )
            )
        row_count_ok = (
            not any(key in expected_table for key in ("row_count", "count"))
            or len(rows)
            == expected_table.get("row_count", expected_table.get("count"))
        )
        checks.append(
            {
                "check": "final_table",
                "passed": bool(table_id)
                and row_count_ok
                and all(row_checks),
                "backend": backend,
                "table_id": table_id,
                "expected": expected_table,
                "actual_rows": rows,
            }
        )

    return {
        "passed": bool(checks) and all(item["passed"] for item in checks),
        "checks": checks,
        "substantive": bool(checks),
    }


def formula_gold_consistency(
    workflow_a: dict[str, Any],
    execution_output: dict[str, Any],
) -> dict[str, Any]:
    """Check generic `.first.FIELD` list-mapping semantics against gold trace."""

    trace = (
        (execution_output.get("details") or {})
        .get("raw_execution", {})
        .get("trace")
        or []
    )
    trace_by_as = {
        str(row.get("as")): row
        for row in trace
        if isinstance(row, dict) and row.get("as") not in (None, "")
    }
    issues: list[dict[str, Any]] = []
    for node in workflow_a.get("nodes") or []:
        configured = node.get("configured_arguments") or {}
        realized_call = trace_by_as.get(str(node.get("source_as") or ""))
        if not realized_call:
            continue
        realized_args = realized_call.get("args") or {}
        for collection_key, mapping in configured.items():
            if not isinstance(mapping, dict) or "____source" not in mapping:
                continue
            realized_items = realized_args.get(collection_key)
            if not isinstance(realized_items, list) or len(realized_items) < 2:
                continue
            for output_field, formula in mapping.items():
                if not isinstance(formula, str):
                    continue
                for match in FIRST_REFERENCE_RE.finditer(formula):
                    source_call = trace_by_as.get(match.group("source_as"))
                    source_rows = (
                        (source_call or {})
                        .get("result", {})
                        .get(match.group("collection"))
                    )
                    if not isinstance(source_rows, list) or not source_rows:
                        continue
                    first_row = source_rows[0]
                    if not isinstance(first_row, dict):
                        continue
                    expected_component = first_row.get(match.group("field"))
                    if expected_component in (None, ""):
                        continue
                    violating = [
                        index
                        for index, item in enumerate(realized_items)
                        if not isinstance(item, dict)
                        or str(expected_component)
                        not in str(item.get(output_field) or "")
                    ]
                    if violating:
                        issues.append(
                            {
                                "issue_id": (
                                    "first_reference_mismatch::"
                                    f"{node.get('node_id')}::{output_field}"
                                ),
                                "kind": "formula_gold_mismatch",
                                "node_id": node.get("node_id"),
                                "source_as": match.group("source_as"),
                                "field": match.group("field"),
                                "expected_first_value": expected_component,
                                "violating_item_indexes": violating,
                                "message": (
                                    "Gold execution does not preserve the "
                                    "configured .first field reference across "
                                    "the mapped output items."
                                ),
                            }
                        )
    return {"passed": not issues, "issues": issues}


def task_discriminativeness(
    model_visible_tools: list[str],
    contracts: list[dict[str, Any]],
    public_runtime_inputs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    contract_hashes = {
        str(contract.get("contract_hash") or "") for contract in contracts
    }
    required_sets = {
        tuple(sorted(contract.get("required_tools") or []))
        for contract in contracts
    }
    issues: list[str] = []
    public_hashes = {
        stable_json_hash(item)
        for item in (public_runtime_inputs or [])
    }
    if (
        len(model_visible_tools) == 1
        and len(contract_hashes) <= 1
        and len(required_sets) <= 1
    ):
        issues.append(
            "Every variant exposes and requires the same single tool with "
            "no distinct observable contract."
        )
    if (
        len(model_visible_tools) == 1
        and len(public_hashes) <= 1
        and len(required_sets) <= 1
    ):
        issues.append(
            "The task has one tool and no variant-level public runtime "
            "variation; hidden state alone determines any differing expected "
            "arguments or result."
        )
    return {
        "passed": not issues,
        "issues": issues,
        "unique_contract_count": len(contract_hashes),
        "unique_required_tool_sets": len(required_sets),
        "model_visible_tool_count": len(model_visible_tools),
        "unique_public_runtime_inputs": len(public_hashes),
    }


def q_only_solver_input_hash(
    task_query: str,
    documentation: dict[str, Any],
    variant_input: dict[str, Any],
    observable_contract: dict[str, Any],
    *,
    workflow_a: dict[str, Any] | None = None,
    protocol_version: str = Q_ONLY_SOLVER_PROTOCOL_VERSION,
) -> str:
    """Fingerprint exactly the public solver input plus evaluator contract ID."""

    callable_tool = "workato_service.call_service"
    uses_seeded_callable_fixture = (
        callable_tool in (observable_contract.get("required_tools") or [])
        or any(
            str(effect.get("tool") or "") == callable_tool
            for effect in observable_contract.get("required_effects") or []
            if isinstance(effect, dict)
        )
    )
    effective_protocol = (
        (
            f"{protocol_version}+seeded-callable-exact-fixtures"
            "+reply-output-projection"
        )
        if uses_seeded_callable_fixture
        else protocol_version
    )

    return stable_json_hash(
        {
            "solver_protocol_version": effective_protocol,
            "Q": task_query,
            "D": documentation,
            "runtime_input": canonical_public_runtime_input(
                variant_input,
                workflow_a,
            ),
            "observable_contract_hash": observable_contract["contract_hash"],
        }
    )
