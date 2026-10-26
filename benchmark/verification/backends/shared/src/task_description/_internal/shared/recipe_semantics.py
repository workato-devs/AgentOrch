from __future__ import annotations

import json
import re
from typing import Any, Iterable


_DP_RE = re.compile(r"_dp\('(?P<payload>\{.*?\})'\)")
_DATA_RE = re.compile(
    r"_\('data\.(?P<path>[^']+)'(?:\s*,\s*'(?P<kind>[^']+)')?\)"
)
_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEARCH_METADATA = {
    "field_list",
    "limit",
    "offset",
    "sobject_name",
    "table_list",
}


def humanize(value: Any) -> str:
    text = str(value or "").replace("$", " ").replace(".", " ")
    text = _CAMEL_RE.sub(" ", text)
    text = re.sub(r"[_\-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def walk_values(value: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk_values(item, path + (str(key),))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk_values(item, path + (str(index),))
    else:
        yield path, value


def references(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _, item in walk_values(value):
        if not isinstance(item, str):
            continue
        for match in _DP_RE.finditer(item):
            try:
                payload = json.loads(match.group("payload"))
            except json.JSONDecodeError:
                continue
            reference = {
                "dialect": "datapill",
                "provider": payload.get("provider"),
                "line": str(payload.get("line") or ""),
                "path": payload.get("path") or [],
                "pill_type": payload.get("pill_type"),
            }
            if payload.get("key") is not None:
                # foreach_meta datapills encode their observable field as
                # ``key`` rather than ``path``.  Retain it so coverage
                # instrumentation can bind the executed iteration index.
                reference["key"] = payload.get("key")
            key = json.dumps(reference, sort_keys=True, ensure_ascii=False)
            if key not in seen:
                seen.add(key)
                result.append(reference)
        for match in _DATA_RE.finditer(item):
            parts = match.group("path").split(".")
            if len(parts) < 2:
                continue
            reference = {
                "dialect": "data_path",
                "provider": parts[0],
                "line": parts[1],
                "path": parts[2:],
                "source_kind": match.group("kind"),
            }
            key = json.dumps(reference, sort_keys=True, ensure_ascii=False)
            if key not in seen:
                seen.add(key)
                result.append(reference)
    return result


def reference_label(reference: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in reference.get("path") or []:
        if isinstance(item, (str, int)):
            parts.append(humanize(item))
        elif isinstance(item, dict):
            marker = item.get("path_element_type")
            if marker == "size":
                parts.append("count")
            elif marker == "current_item":
                parts.append("each item")
    label = " ".join(part for part in parts if part)
    provider = str(reference.get("provider") or "")
    if provider == "catch" and label == "message":
        return "caught error message"
    if provider in {"workato_service", "workato_api_platform"} and label.startswith(
        "request "
    ):
        return label
    return label or humanize(provider) or "referenced value"


def reference_labels(value: Any) -> list[str]:
    return list(dict.fromkeys(reference_label(item) for item in references(value)))


def _quoted(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return f'"{value}"'


def describe_value(value: Any) -> str:
    labels = reference_labels(value)
    if labels:
        if len(labels) == 1:
            return labels[0]
        return ", then ".join(labels)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return _quoted(value)


def condition_summary(condition: Any) -> str:
    if not isinstance(condition, dict):
        return describe_value(condition)
    clauses: list[str] = []
    operand_names = {
        "blank": "is blank",
        "present": "is present",
        "greater_than": "is greater than",
        "less_than": "is less than",
        "equals": "equals",
        "equal_to": "equals",
        "not_equal_to": "does not equal",
        "contains": "contains",
    }
    for item in condition.get("conditions") or []:
        if not isinstance(item, dict):
            continue
        left = describe_value(item.get("lhs"))
        operand = str(item.get("operand") or "matches")
        phrase = operand_names.get(operand, humanize(operand))
        if operand in {"blank", "present"}:
            clauses.append(f"{left} {phrase}")
        else:
            clauses.append(f"{left} {phrase} {describe_value(item.get('rhs'))}")
    if not clauses:
        return "the configured condition is satisfied"
    joiner = " and " if str(condition.get("operand") or "and") == "and" else " or "
    return joiner.join(clauses)


def _selected_fields(arguments: dict[str, Any]) -> list[str]:
    value = arguments.get("field_list")
    if isinstance(value, list):
        fields = [str(item) for item in value]
    elif isinstance(value, str):
        fields = re.split(r"[\n,]+", value)
    else:
        fields = []
    return [item.strip() for item in fields if item.strip()]


def _configured_objects(
    arguments: dict[str, Any],
    dynamic: dict[str, Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for key in (
        "sobject_name",
        "object_name",
        "sobject",
        "table_id",
        "lookup_table_id",
        "sheet",
        "spreadsheet",
    ):
        if arguments.get(key) not in (None, ""):
            result.append({"parameter": key, "value": arguments[key]})
    if dynamic.get("sobject_name") not in (None, ""):
        display = dynamic["sobject_name"]
        if not any(item.get("value") == display for item in result):
            result.append(
                {
                    "parameter": "dynamicPickListSelection.sobject_name",
                    "value": display,
                    "display_only": True,
                }
            )
    return result


def _configured_fields(
    tool: str,
    arguments: dict[str, Any],
    dynamic: dict[str, Any],
) -> dict[str, Any]:
    selected = [
        {"name": item, "label": humanize(item)}
        for item in _selected_fields(arguments)
    ]
    dynamic_selected = dynamic.get("field_list")
    if isinstance(dynamic_selected, list):
        for item in dynamic_selected:
            if not isinstance(item, dict):
                continue
            value = str(item.get("value") or "")
            existing = next(
                (field for field in selected if field["name"] == value),
                None,
            )
            if existing is not None:
                existing["label"] = str(
                    item.get("label") or existing["label"]
                )
            elif value:
                selected.append(
                    {
                        "name": value,
                        "label": str(item.get("label") or humanize(value)),
                    }
                )
    filters: list[dict[str, Any]] = []
    if tool == "salesforce.search_sobjects":
        for key, value in arguments.items():
            if key in _SEARCH_METADATA:
                continue
            labels = reference_labels(value)
            value_summary = (
                "the first value that is neither false nor null from "
                + ", ".join(labels)
                + "; blank strings are retained"
                if isinstance(value, str)
                and " or " in value
                and len(labels) > 1
                else describe_value(value)
            )
            filters.append(
                {
                    "field": key,
                    "value": value,
                    "value_summary": value_summary,
                    "predicate": "equals",
                }
            )
    return {"selected": selected, "filters": filters}


def _formulas(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path, value in walk_values(arguments):
        if not isinstance(value, str):
            continue
        if (
            value.lstrip().startswith("=")
            or "_dp(" in value
            or "_('data." in value
        ):
            result.append(
                {
                    "path": ".".join(path),
                    "expression": value,
                    "references": reference_labels(value),
                }
            )
    return result


def _fallback_chains(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path, value in walk_values(arguments):
        if (
            not isinstance(value, str)
            or " or " not in value
            or not (
                value.lstrip().startswith("=")
                or "_dp(" in value
                or "_('data." in value
            )
        ):
            continue
        alternatives = reference_labels(value)
        if len(alternatives) < 2:
            continue
        result.append(
            {
                "path": ".".join(path),
                "expression": value,
                "ordered_alternatives": alternatives,
            }
        )
    return result


def _response_field_summary(name: str, value: Any) -> str:
    label = humanize(name)
    if isinstance(value, dict) and "____source" in value:
        mapped = [
            (
                "joined date"
                if humanize(key) == "joined"
                else humanize(key)
            )
            for key in value
            if not key.startswith("____")
        ]
        return f"{label} as a list mapped with {', '.join(mapped)}"
    if isinstance(value, str):
        lowered = value.lower()
        refs = reference_labels(value)
        if "smart_join" in lowered:
            separator_match = re.search(r"smart_join\([\"'](?P<sep>.*?)[\"']\)", value)
            separator = separator_match.group("sep") if separator_match else "the configured separator"
            pluck_match = re.search(
                r"\.pluck\([\"'](?P<field>.*?)[\"']\)",
                value,
            )
            joined_values = (
                f"{humanize(pluck_match.group('field'))} values"
                if pluck_match
                else "referenced values"
            )
            return (
                f"{label} as {joined_values} joined with {_quoted(separator)} "
                "when rows exist, otherwise null"
            )
        if any(
            isinstance(item, dict) and item.get("path_element_type") == "size"
            for ref in references(value)
            for item in ref.get("path") or []
        ):
            return f"{label} as the number of referenced rows"
        if refs:
            return f"{label} from {', then '.join(refs)}"
    return f"{label} as {describe_value(value)}"


def _response_contract(tool: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
    is_response_action = any(
        token in tool
        for token in ("reply", "return_response", "return_result")
    )
    if not is_response_action:
        return None
    body_key = next(
        (
            key
            for key in ("response", "reply", "result", "message")
            if key in arguments
        ),
        None,
    )
    if body_key is None:
        return None
    body = arguments.get(body_key) if body_key is not None else None
    field_summaries = (
        [
            _response_field_summary(str(key), value)
            for key, value in body.items()
        ]
        if isinstance(body, dict)
        else []
    )
    return {
        "reply_type": arguments.get("reply_type"),
        "http_status_code": arguments.get("http_status_code"),
        "body_argument": body_key,
        "body": body,
        "field_summaries": field_summaries,
    }


def configured_semantics(node: dict[str, Any]) -> dict[str, Any]:
    arguments = (
        node.get("arguments") if isinstance(node.get("arguments"), dict) else {}
    )
    dynamic = (
        node.get("dynamic_pick_list_selection")
        if isinstance(node.get("dynamic_pick_list_selection"), dict)
        else {}
    )
    tool = str(node.get("tool_name") or "")
    predicates: list[dict[str, Any]] = []
    if isinstance(node.get("condition"), dict):
        predicates.append(
            {
                "kind": "control_condition",
                "configured": node["condition"],
                "summary": condition_summary(node["condition"]),
            }
        )
    fields = _configured_fields(tool, arguments, dynamic)
    predicates.extend(
        {
            "kind": "field_equality",
            "field": item["field"],
            "configured": item["value"],
            "summary": (
                f"{humanize(item['field'])} equals {item['value_summary']}"
            ),
        }
        for item in fields["filters"]
    )
    return {
        "configured_arguments": arguments,
        "configured_objects": _configured_objects(arguments, dynamic),
        "configured_fields": fields,
        "predicates": predicates,
        "fallback_chains": _fallback_chains(arguments),
        "formulas": _formulas(arguments),
        "response_contract": _response_contract(tool, arguments),
    }


def node_description(node: dict[str, Any]) -> str:
    keyword = str(node.get("source_keyword") or "")
    tool = str(node.get("tool_name") or "")
    arguments = node.get("arguments") or {}
    semantics = configured_semantics(node)
    if keyword in {"if", "elsif", "while_condition"}:
        return f"Check whether {condition_summary(node.get('condition'))}."
    if keyword == "else":
        return "Handle the fall-through path when the preceding condition is false."
    if keyword == "try":
        return "Run the enclosed business processing with an exception handler."
    if keyword == "catch":
        return "Handle an exception from the protected business processing."
    if keyword == "foreach":
        source = describe_value(arguments.get("source"))
        return f"Process each item in {source}."
    if keyword == "repeat":
        return "Repeat the enclosed processing according to its configured limit."
    if keyword == "stop":
        return "Explicitly stop the current recipe."
    if keyword == "trigger":
        return "Receive the configured public request."
    if tool == "salesforce.search_sobjects":
        objects = semantics["configured_objects"]
        object_name = (
            humanize(objects[0]["value"]) if objects else "configured records"
        )
        filters = [
            item["summary"] for item in semantics["predicates"]
            if item.get("kind") == "field_equality"
        ]
        selected = [
            str(item.get("label") or humanize(item["name"]))
            for item in semantics["configured_fields"]["selected"]
        ]
        description = f"Find {object_name} records in Salesforce"
        if filters:
            description += " where " + " and ".join(filters)
        if selected:
            description += ", returning " + ", ".join(selected)
        return description + "."
    if tool == "workato_service.send_reply":
        response = semantics.get("response_contract") or {}
        reply_type = humanize(response.get("reply_type") or "configured")
        if response.get("body_argument") == "message":
            message = response.get("body")
            labels = reference_labels(message)
            article = "an" if reply_type[:1].lower() in "aeiou" else "a"
            if labels:
                return (
                    f"Send {article} {reply_type} reply using "
                    f"{', then '.join(labels)}."
                )
            return (
                f"Send {article} {reply_type} reply with message "
                f"{_quoted(message)}."
            )
        fields = response.get("field_summaries") or []
        if fields:
            return (
                f"Send a {reply_type} reply containing "
                + "; ".join(fields)
                + "."
            )
        article = "an" if reply_type[:1].lower() in "aeiou" else "a"
        return f"Send the configured {article} {reply_type} reply."
    if tool == "workato_api_platform.return_response":
        response = semantics.get("response_contract") or {}
        status = response.get("http_status_code") or "200"
        fields = response.get("field_summaries") or []
        suffix = f" containing {'; '.join(fields)}" if fields else ""
        return f"Return HTTP {status} to the caller{suffix} and stop processing."
    if tool.endswith(".return_result") or tool.endswith(
        ".workflow_return_result"
    ):
        response = semantics.get("response_contract") or {}
        fields = response.get("field_summaries") or []
        suffix = f" containing {'; '.join(fields)}" if fields else ""
        return f"Return the result to the caller{suffix} and stop processing."
    if tool == "workato_smart_list.query_list":
        sql = str(arguments.get("sql") or "").strip()
        normalized = re.sub(r"\s+", " ", sql).strip()
        return (
            f"Apply the configured in-memory data operation: {normalized}."
            if normalized
            else "Apply the configured in-memory data operation."
        )
    if tool == "logger.log_message":
        return f"Render the configured log message from {describe_value(arguments.get('message'))}."
    operation = humanize(tool.rsplit(".", 1)[-1] if tool else keyword)
    objects = semantics["configured_objects"]
    target = f" for {humanize(objects[0]['value'])}" if objects else ""
    return f"Perform the configured {operation}{target}."


def observable_derivation_description(node: dict[str, Any]) -> str | None:
    tool = str(node.get("tool_name") or "")
    arguments = node.get("arguments") or {}
    if tool != "workato_smart_list.query_list":
        return None
    sql = re.sub(r"\s+", " ", str(arguments.get("sql") or "")).strip()
    match = re.match(
        r"SELECT\s+(?P<fields>.+?)\s+FROM\s+(?P<table>\S+)"
        r"(?:\s+ORDER\s+BY\s+(?P<order>.+))?$",
        sql,
        flags=re.I,
    )
    if not match:
        return None
    table = humanize(match.group("table"))
    fields_list = [
        humanize(item.strip()) for item in match.group("fields").split(",")
    ]
    fields = ", ".join(fields_list)
    order = match.group("order")
    if order:
        order_words = humanize(order)
        if order_words.lower().startswith("joined "):
            order_words = "joined date " + order_words[len("joined "):]
        return (
            f"Order the {fields} rows by {order_words} before constructing "
            "the response."
        )
    return f"Use {fields} from the resulting rows."


def evidence_requirements(node: dict[str, Any]) -> list[dict[str, Any]]:
    semantics = configured_semantics(node)
    requirements: list[dict[str, Any]] = []

    def add(fact: str, *alternatives: str) -> None:
        values = [item for item in alternatives if item]
        if values:
            requirements.append(
                {"fact": fact, "any_of": list(dict.fromkeys(values))}
            )

    for item in semantics["configured_objects"]:
        if not item.get("display_only"):
            value = str(item["value"])
            add(f"configured object {value}", value, humanize(value))
    for item in semantics["configured_fields"]["filters"]:
        field = str(item["field"])
        add(f"filter field {field}", field, humanize(field))
        value_labels = reference_labels(item["value"])
        for label in value_labels:
            add(f"filter value {label}", label, humanize(label))
        if not value_labels and item["value"] not in (None, ""):
            value = str(item["value"])
            add(f"filter value {value}", value, humanize(value))
    for item in semantics["configured_fields"]["selected"]:
        field = str(item["name"])
        label = str(item.get("label") or "")
        add(
            f"selected field {field}",
            field,
            humanize(field),
            label,
            humanize(label),
        )
    response = semantics.get("response_contract")
    if response:
        reply_type = response.get("reply_type")
        if reply_type:
            add(f"reply type {reply_type}", str(reply_type))
        body = response.get("body")
        if response.get("body_argument") == "message" and isinstance(body, str):
            if not reference_labels(body):
                add("exact configured message", body)
            else:
                for label in reference_labels(body):
                    add(f"reply message source {label}", label, humanize(label))
        if isinstance(body, dict):
            for path, value in walk_values(body):
                if not path:
                    continue
                key = path[-1]
                if key.startswith("____"):
                    continue
                add(f"response field {key}", str(key), humanize(key))
                if isinstance(value, str) and "smart_join" in value:
                    separator_match = re.search(
                        r"smart_join\([\"'](?P<sep>.*?)[\"']\)", value
                    )
                    if separator_match:
                        separator = separator_match.group("sep")
                        add(
                            f"response join separator {separator}",
                            separator,
                        )
                    if re.search(r"\b(?:nil|null)\b", value, flags=re.I):
                        add("response fallback null", "null")
    if isinstance(node.get("condition"), dict):
        for label in reference_labels(node["condition"]):
            add(f"condition input {label}", label, humanize(label))
        for item in node["condition"].get("conditions") or []:
            if isinstance(item, dict) and item.get("operand"):
                operand = str(item["operand"])
                add(f"condition operator {operand}", operand, humanize(operand))
    return requirements
