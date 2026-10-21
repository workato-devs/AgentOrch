"""Fail-closed parity between a frozen WorkflowPlan and one simulator run.

The raw recipe remains the only ground-truth program.  Stage 7 serializes that
program as ``WorkflowPlanV1`` and separately records the recipe's concrete
simulator execution as an ActiveTrace.  This module verifies that the two
views still denote the same executed episode; it does not repair either view
or accept semantic alternatives.

The report is intentionally independent of the publication pipeline.  Stage 7
can construct it before writing artifacts and refuse publication when
``passed`` is false.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import csv
import io
from itertools import product
import json
import re
import unicodedata
from typing import Any, Iterable

from .pipeline_common import INHERENTLY_TERMINAL_TOOLS, stable_json_hash
from .exact_trace_normalization import (
    canonical_exact_argument_view,
    exact_arguments_equal,
)


REPORT_SCHEMA_VERSION = "agentorch-workflow-plan-variant-replay-consistency-v1"


class ReplayResolutionError(RuntimeError):
    """A frozen symbolic value cannot be resolved from executed evidence."""


class _WorkatoSkip:
    pass


_WORKATO_SKIP = _WorkatoSkip()


def _workato_inspect(value: Any) -> str:
    """Ruby-compatible inspect used by Workato text action boundaries."""

    if value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        escaped = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\t", "\\t")
            .replace("\r", "\\r")
        )
        return f'"{escaped}"'
    if isinstance(value, list):
        return "[" + ", ".join(_workato_inspect(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(
            f"{_workato_inspect(key)}=>{_workato_inspect(item)}"
            for key, item in value.items()
        ) + "}"
    return str(value)


def _workato_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return _workato_inspect(value)
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def _iter_plan_nodes(nodes: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for node in nodes:
        if not isinstance(node, dict):
            continue
        yield node
        for key in ("workflow", "then", "else", "body", "catch"):
            children = node.get(key)
            if isinstance(children, list):
                yield from _iter_plan_nodes(children)


def _runtime_inputs(public_runtime_input: dict[str, Any] | None) -> dict[str, Any]:
    value = public_runtime_input or {}
    trigger = value.get("trigger_input")
    if not isinstance(trigger, dict):
        # Unit callers and pre-publication code may already pass the canonical
        # trigger object rather than its publication envelope.
        trigger = value
    result = deepcopy(trigger) if isinstance(trigger, dict) else {}
    execution_context = value.get("execution_context")
    if isinstance(execution_context, dict):
        result["execution_context"] = deepcopy(execution_context)
    return result


def _replace_runtime_tokens(value: Any, replacements: dict[str, str]) -> Any:
    """Resolve private provisioning tokens for replay-only comparison."""

    if isinstance(value, dict):
        return {
            key: _replace_runtime_tokens(child, replacements)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_replace_runtime_tokens(child, replacements) for child in value]
    if isinstance(value, str):
        for token, resolved in sorted(
            replacements.items(), key=lambda item: len(item[0]), reverse=True
        ):
            value = value.replace(token, resolved)
    return value


def _provisioned_runtime_tokens(simulator_execution: Any) -> dict[str, str]:
    """Read token-to-live-value evidence emitted by the private seed harness."""

    if not isinstance(simulator_execution, dict):
        return {}
    replacements: dict[str, str] = {}
    ambiguous: set[str] = set()
    calls = (simulator_execution.get("details") or {}).get(
        "seed_harness_tool_calls"
    ) or []
    for call in calls:
        if not isinstance(call, dict):
            continue
        refs = (((call.get("result") or {}).get("state") or {}).get("refs") or {})
        if not isinstance(refs, dict):
            continue
        for token, resolved in refs.items():
            token_text = str(token)
            if not token_text.startswith("$") or resolved in (None, ""):
                continue
            resolved_text = str(resolved)
            if token_text in ambiguous:
                continue
            previous = replacements.get(token_text)
            if previous is not None and previous != resolved_text:
                # Generic object-type aliases (for example
                # ``$GONG__GONG_CALL__C_ID``) may legitimately be rebound by
                # later seed phases. They are not a stable token-to-value
                # mapping and therefore cannot be used as replay evidence.
                # Keep uniquely named refs, but leave an ambiguous token
                # unresolved so an actual public-input dependency still
                # fails exact argument comparison instead of crashing the
                # whole corpus audit.
                replacements.pop(token_text, None)
                ambiguous.add(token_text)
                continue
            replacements[token_text] = resolved_text
    return replacements


def _lookup(value: Any, path: Iterable[Any]) -> Any:
    current = value
    parts = list(path)
    index = 0
    while index < len(parts):
        raw_part = parts[index]
        part: Any = raw_part
        if isinstance(raw_part, str) and raw_part.lstrip("-").isdigit():
            part = int(raw_part)
        if current is None:
            if (
                len(parts) - index >= 2
                and parts[-2] in {"<first>", "first"}
                and parts[-1] == "____Size"
            ):
                return 0
            return None
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, dict) and isinstance(part, str):
            dotted_match = next(
                (
                    (end, ".".join(str(item) for item in parts[index:end]))
                    for end in range(len(parts), index + 1, -1)
                    if ".".join(str(item) for item in parts[index:end]) in current
                ),
                None,
            )
            if dotted_match is not None:
                end, key = dotted_match
                current = current[key]
                index = end
                continue
            # Dynamic Snowflake output schemas give datapills stable-looking
            # editor keys such as ``account_id_54508f65``.  The connector
            # result deliberately projects those columns to their declared
            # canonical names (``account_id``).  Resolve that documented
            # representation bridge only when the exact suffixed key is not
            # present; ordinary object lookup continues to take precedence.
            dynamic_column = re.fullmatch(r"(.+)_([0-9a-fA-F]{8})", part)
            canonical_part = dynamic_column.group(1) if dynamic_column else ""
            if canonical_part and canonical_part in current:
                current = current[canonical_part]
            else:
                return None
        elif isinstance(part, str) and part in {"<size>", "size", "length"}:
            if not isinstance(current, (dict, list, tuple, str)):
                raise ReplayResolutionError(
                    f"cannot take size of {type(current).__name__}"
                )
            current = len(current)
        elif isinstance(part, str) and part in {
            "<first>",
            "first",
            "<current_item>",
        }:
            # Workato encodes list metadata as
            # ``collection.first.____Size``.  ``____Size`` describes the
            # collection even when it is empty; it is not a property of the
            # first row.  RawRecipeExecutor applies this same list_meta
            # fallback in resolve_data_call.
            if (
                part in {"<first>", "first"}
                and index + 1 < len(parts)
                and parts[index + 1] == "____Size"
            ):
                if not isinstance(current, (list, tuple)):
                    raise ReplayResolutionError(
                        "list metadata ____Size requires an executed collection, "
                        f"got {type(current).__name__}"
                    )
                current = len(current)
                index += 2
                continue
            if not isinstance(current, (list, tuple)):
                raise ReplayResolutionError(
                    f"{part} requires an executed collection, got "
                    f"{type(current).__name__}"
                )
            current = current[0] if current else None
        elif isinstance(current, (list, tuple)) and isinstance(part, int):
            current = current[part] if -len(current) <= part < len(current) else None
        else:
            return None
        index += 1
    return current


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
    """Coerce a Workato/Ruby numeric operand without changing text fields."""

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
    raise ReplayResolutionError(f"formula value is not numeric: {value!r}")


def _integer_like(value: Any) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
    ) or (
        isinstance(value, str)
        and re.fullmatch(r"[+-]?\d+", value.strip()) is not None
    )


def _path_exists(value: Any, path: Iterable[Any]) -> bool:
    """Return whether ``path`` is structurally present, including null values."""

    current = value
    parts = list(path)
    if not parts:
        return current is not None
    for raw_part in parts:
        part: Any = raw_part
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


def _blank(value: Any) -> bool:
    return value is _WORKATO_SKIP or value in (None, "", [], {})


def _integer(value: Any) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, (int, float, bool)):
        return int(value)
    match = re.match(r"^[+-]?\d+", str(value).strip())
    return int(match.group(0)) if match else 0


def _datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReplayResolutionError(f"cannot parse Workato time {value!r}") from exc
    return result if result.tzinfo else result.replace(tzinfo=timezone.utc)


def _shift_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    last_day = (next_month - timedelta(days=1)).day
    return value.replace(year=year, month=month, day=min(value.day, last_day))


def _matches(value: Any, expected: Any) -> bool:
    if isinstance(expected, dict) and "$regex" in expected:
        payload = expected["$regex"]
        pattern = payload.get("pattern", "") if isinstance(payload, dict) else str(payload)
        flags = re.IGNORECASE if isinstance(payload, dict) and "i" in payload.get("flags", "") else 0
        return re.search(pattern, str(value or ""), flags) is not None
    if isinstance(expected, list):
        return value in expected
    return value == expected


def _where(rows: Any, conditions: Any) -> list[Any]:
    if not isinstance(rows, list) or not isinstance(conditions, dict):
        return []
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        accepted = True
        for raw_key, expected in conditions.items():
            key = str(raw_key)
            negate = key.endswith(" !=")
            field = key[:-3] if negate else key
            if _matches(row.get(field), expected) == negate:
                accepted = False
                break
        if accepted:
            result.append(row)
    return result


def _method(method: str, receiver: Any, args: list[Any], inputs: dict[str, Any]) -> Any:
    if method == "presence": return None if _blank(receiver) else receiver
    if method == "present?": return not _blank(receiver)
    if method == "blank?": return _blank(receiver)
    if method == "is_true?": return receiver is True or str(receiver).lower() == "true"
    if method == "is_not_true?": return not (receiver is True or str(receiver).lower() == "true")
    if method == "to_i": return _integer(receiver)
    if method == "to_f": return float(receiver or 0)
    if method == "to_s": return _workato_text(receiver)
    if method == "to_json": return json.dumps(receiver, ensure_ascii=False, separators=(",", ":"))
    if method in {"downcase", "upcase", "capitalize", "titleize", "unicode_normalize"}:
        text = str(receiver or "")
        return {"downcase": text.lower, "upcase": text.upper, "capitalize": text.capitalize,
                "titleize": lambda: re.sub(
                    r"[A-Za-z0-9]+",
                    lambda match: match.group(0).capitalize(),
                    text.replace("_", " "),
                ),
                "unicode_normalize": lambda: unicodedata.normalize("NFC", text)}[method]()
    if method == "strip": return str(receiver or "").strip()
    if method == "lstrip": return str(receiver or "").lstrip()
    if method == "split": return str(receiver or "").split(str(args[0]) if args else None)
    if method == "include?": return bool(args) and args[0] in receiver
    if method == "starts_with?": return str(receiver or "").startswith(str(args[0] if args else ""))
    if method == "ends_with?": return str(receiver or "").endswith(str(args[0] if args else ""))
    if method == "match?": return bool(args) and _matches(receiver, args[0])
    if method == "gsub":
        if len(args) < 2: raise ReplayResolutionError("gsub requires pattern and replacement")
        pattern, replacement = args[0], args[1]
        if isinstance(pattern, dict) and "$regex" in pattern:
            payload = pattern["$regex"]
            regex = payload.get("pattern", "") if isinstance(payload, dict) else str(payload)
            if isinstance(replacement, dict):
                return re.sub(regex, lambda m: str(replacement.get(m.group(0), "")), str(receiver or ""))
            return re.sub(regex, str(replacement), str(receiver or ""))
        return str(receiver or "").replace(str(pattern), str(replacement))
    if method == "slice":
        start = _integer(args[0]) if args else 0
        return receiver[start:start + _integer(args[1])] if len(args) > 1 else receiver[start]
    if method in {"length", "size"}: return len(receiver) if receiver is not None else 0
    if method == "keys": return list(receiver) if isinstance(receiver, dict) else []
    if method == "first": return receiver[0] if receiver else None
    if method == "last": return receiver[-1] if receiver else None
    if method == "pluck":
        paths = args or []
        def get(row: Any, path: Any) -> Any: return _lookup(row, path if isinstance(path, list) else [path])
        return ([get(row, paths[0]) for row in receiver or []] if len(paths) == 1
                else [[get(row, path) for path in paths] for row in receiver or []])
    if method == "compact": return [item for item in receiver or [] if item is not None]
    if method == "concat": return [*receiver, *(args[0] or [])] if isinstance(receiver, list) else str(receiver or "") + str(args[0] if args else "")
    if method == "uniq":
        result = []
        for item in receiver or []:
            if item not in result: result.append(item)
        return result
    if method == "sum": return sum(receiver or [])
    if method == "min": return min(receiver or [], default=None)
    if method == "max": return max(receiver or [], default=None)
    if method == "reverse": return receiver[::-1]
    if method in {"join", "smart_join"}: return str(args[0] if args else "").join(str(item) for item in receiver or [])
    if method == "where": return _where(receiver, args[0] if args else {})
    if method == "format_map":
        template = str(args[0] if args else "")
        return [re.sub(r"%\{([^}]+)\}", lambda m: str(row.get(m.group(1), "")), template)
                for row in receiver or [] if isinstance(row, dict)]
    if method == "to_csv":
        output = io.StringIO(); writer = csv.writer(output, lineterminator="\n")
        for row in receiver or []: writer.writerow(row if isinstance(row, list) else [row])
        return output.getvalue()
    if method in {"to_time", "to_date"}:
        value = _datetime(receiver); return value.isoformat() if method == "to_time" else value.date().isoformat()
    if method == "utc": return _datetime(receiver).astimezone(timezone.utc).isoformat()
    if method == "beginning_of_day": return _datetime(receiver).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    if method == "strftime": return _datetime(receiver).strftime(str(args[0] if args else ""))
    if method == "in_time_zone":
        from zoneinfo import ZoneInfo
        return _datetime(receiver).astimezone(ZoneInfo(str(args[0]))).isoformat()
    if method == "ago":
        if not isinstance(receiver, dict) or "$duration" not in receiver: raise ReplayResolutionError("ago requires duration")
        amount, unit = receiver["$duration"]
        now = _lookup(inputs, ["execution_context", "now"])
        if now in (None, ""): raise ReplayResolutionError("ago requires execution_context.now")
        base = _datetime(now)
        result = (_shift_months(base, -amount * (12 if unit == "years" else 1))
                  if unit in {"months", "years"} else base - timedelta(**{unit: amount}))
        return result.astimezone(timezone.utc).isoformat()
    if method == "wday": return (_datetime(receiver).weekday() + 1) % 7
    if method == "yweek": return _datetime(receiver).isocalendar().week
    if method == "quote": return "'" + str(receiver or "").replace("'", "''") + "'"
    if method == "to_currency": return f"{float(receiver or 0):,.2f}"
    if method == "strip_tags": return re.sub(r"<[^>]+>", "", str(receiver or ""))
    raise ReplayResolutionError(f"unsupported Workato method {method!r}")


def _slack_block_lines_resolved(block: Any) -> list[str]:
    if not isinstance(block, dict):
        return []
    lines: list[str] = []
    if block.get("section_text") not in (None, ""):
        lines.append(str(block["section_text"]))
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
        raise ReplayResolutionError("slack_text requires an object")
    lines: list[str] = []
    for block in raw_input.get("blocks") or []:
        lines.extend(_slack_block_lines_resolved(block))
    if raw_input.get("text") not in (None, ""):
        lines.append(str(raw_input["text"]))
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
        title, value = field.get("title"), field.get("value")
        if title not in (None, "") or value not in (None, ""):
            lines.append(f"{'' if title is None else title}: {'' if value is None else value}")
    text = "\n".join(lines)
    if not text:
        raise ReplayResolutionError("Slack message rendered empty text")
    return re.sub(r"<anon>(.*?)</anon>", r"\1", text, flags=re.DOTALL)


def _slack_attachments_resolved(raw_input: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_input, dict):
        raise ReplayResolutionError("slack_attachments requires an object")
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


def _legacy_reference(value: dict[str, Any], kind: str) -> tuple[str, list[Any]]:
    payload = value.get(kind)
    if kind == "input_ref":
        if isinstance(payload, str):
            return payload, [item for item in payload.split(".") if item]
        if isinstance(payload, list):
            return "", list(payload)
        if isinstance(payload, dict):
            raw_path = payload.get("path") or []
            return "", list(raw_path) if isinstance(raw_path, list) else []
        return "", []
    if not isinstance(payload, dict):
        raise ReplayResolutionError(f"{kind} payload is not an object")
    source = str(
        payload.get("node")
        or payload.get("source_node")
        or payload.get("binding")
        or payload.get("bind")
        or ""
    )
    raw_path = payload.get("path") or []
    path = list(raw_path) if isinstance(raw_path, list) else []
    return source, path


def _resolve_value(
    value: Any,
    *,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    loops: dict[str, Any],
    errors: dict[str, Any],
    resources: dict[str, Any],
) -> Any:
    """Resolve compiler legacy values and normalized WorkflowPlan values."""

    if not isinstance(value, dict):
        raise ReplayResolutionError("symbolic value is not an object")

    if set(value) == {"literal"}:
        return deepcopy(value["literal"])
    if set(value) == {"input_ref"}:
        _, path = _legacy_reference(value, "input_ref")
        return _lookup(inputs, path)
    for kind, state in (
        ("output_ref", outputs),
        ("loop_ref", loops),
        ("error_ref", errors),
    ):
        if set(value) == {kind}:
            source, path = _legacy_reference(value, kind)
            if not source or source not in state:
                raise ReplayResolutionError(
                    f"{kind} source {source!r} has no executed evidence"
                )
            return _lookup(state[source], path)
    if set(value) == {"resource_ref"}:
        payload = value["resource_ref"]
        if isinstance(payload, str):
            name, path = payload, []
        elif isinstance(payload, dict):
            name = str(payload.get("resource") or payload.get("name") or "")
            path = list(payload.get("path") or [])
        else:
            raise ReplayResolutionError("resource_ref payload is invalid")
        if name not in resources:
            raise ReplayResolutionError(f"resource {name!r} has no public evidence")
        return _lookup(resources[name], path)

    kind = str(value.get("kind") or "")
    if kind == "literal":
        return deepcopy(value.get("value"))
    if kind == "input_ref":
        raw_path = value.get("path") or []
        path = raw_path.split(".") if isinstance(raw_path, str) else list(raw_path)
        return _lookup(inputs, path)
    if kind in {"output_ref", "loop_ref", "error_ref"}:
        state = {
            "output_ref": outputs,
            "loop_ref": loops,
            "error_ref": errors,
        }[kind]
        source = str(value.get("binding") or value.get("node") or "")
        if not source or source not in state:
            raise ReplayResolutionError(
                f"{kind} source {source!r} has no executed evidence"
            )
        return _lookup(state[source], value.get("path") or [])
    if kind == "resource_ref":
        name = str(value.get("resource") or "")
        if name not in resources:
            raise ReplayResolutionError(f"resource {name!r} has no public evidence")
        return _lookup(resources[name], value.get("path") or [])

    expression = value.get("expression") if set(value) == {"expression"} else value
    if not isinstance(expression, dict):
        raise ReplayResolutionError("expression payload is invalid")
    op = str(expression.get("op") or "")
    if not op:
        # A JSON-shaped container is accepted only when every leaf remains a
        # symbolic value.  This mirrors WorkflowPlan's deterministic object
        # shorthand and never treats raw scalar constants as bindings.
        result: dict[str, Any] = {}
        for key, child in expression.items():
            resolved = _resolve_value(
                child,
                inputs=inputs,
                outputs=outputs,
                loops=loops,
                errors=errors,
                resources=resources,
            )
            if resolved is not _WORKATO_SKIP:
                result[str(key)] = resolved
        return result

    def resolve(child: Any) -> Any:
        return _resolve_value(
            child,
            inputs=inputs,
            outputs=outputs,
            loops=loops,
            errors=errors,
            resources=resources,
        )

    if op == "object":
        result: dict[str, Any] = {}
        for key, child in (expression.get("fields") or {}).items():
            resolved = resolve(child)
            if resolved is not _WORKATO_SKIP:
                result[str(key)] = resolved
        return result
    if op == "array":
        resolved_items = [
            resolve(child) for child in expression.get("items") or []
        ]
        return [item for item in resolved_items if item is not _WORKATO_SKIP]
    if op == "interpolate":
        return "".join(
            "" if (resolved := resolve(child)) is None else str(resolved)
            for child in expression.get("parts") or expression.get("args") or []
        )

    if op in {"map", "project", "filter"}:
        raw_items = expression.get("args") or expression.get("items") or []
        if len(raw_items) != 1:
            raise ReplayResolutionError(f"{op} requires one collection")
        collection = resolve(raw_items[0]) or []
        if isinstance(collection, dict):
            collection = [collection]
        binding = str(expression.get("item_bind") or "")
        if not binding:
            raise ReplayResolutionError(f"{op} requires item_bind")
        previous = loops.get(binding)
        existed = binding in loops
        result = []
        try:
            for item in collection:
                loops[binding] = item
                if op == "filter":
                    if bool(resolve(expression.get("condition"))):
                        result.append(item)
                else:
                    projected = resolve(expression.get("value"))
                    if projected is not _WORKATO_SKIP:
                        result.append(projected)
        finally:
            if existed: loops[binding] = previous
            else: loops.pop(binding, None)
        return result

    if op == "if":
        condition = expression.get("condition")
        choices = expression.get("args") or []
        if condition is None and len(choices) == 3:
            condition, choices = choices[0], choices[1:]
        if condition is None or len(choices) != 2:
            raise ReplayResolutionError("if expression has incomplete operands")
        return resolve(choices[0] if bool(resolve(condition)) else choices[1])

    if op in {"coalesce", "ruby_or"}:
        children = expression.get("args") or []
        if not children:
            return None
        last: Any = None
        for child in children:
            last = resolve(child)
            blank = _blank(last)
            if op == "ruby_or":
                blank = blank or last is False
            if not blank:
                return last
        return last

    args = [resolve(child) for child in expression.get("args") or []]
    if op == "get":
        return _lookup(args[0] if args else None, expression.get("path") or [])
    if op == "path_exists":
        return _path_exists(args[0] if args else None, expression.get("path") or [])
    if op in {"count", "length"}:
        return len(args[0]) if args and args[0] is not None else 0
    if op == "is_blank":
        return _blank(args[0] if args else None)
    if op == "is_present":
        return not _blank(args[0] if args else None)
    if op == "eq":
        return len(args) >= 2 and args[0] == args[1]
    if op == "ne":
        return len(args) >= 2 and args[0] != args[1]
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
            left, right = _arithmetic_number(left), _arithmetic_number(right)
        try:
            if op == "gt":
                return left > right
            if op == "gte":
                return left >= right
            if op == "lt":
                return left < right
            return left <= right
        except TypeError as exc:
            raise ReplayResolutionError(
                f"{op} operands are not comparable: "
                f"{type(left).__name__} and {type(right).__name__}"
            ) from exc
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
    if op == "join":
        collection = args[0] if args else []
        separator = args[1] if len(args) > 1 else ""
        return str(separator).join(str(item) for item in collection or [])
    if op in {"lower", "upper"}:
        text = str(args[0] if args else "")
        return text.lower() if op == "lower" else text.upper()
    if op == "workato_skip": return _WORKATO_SKIP
    if op == "workato_clear": return ""
    if op == "workato_text":
        if len(args) != 1:
            raise ReplayResolutionError("workato_text requires one operand")
        return _workato_text(args[0])
    if op in {"workato_now", "workato_today"}:
        configured = _lookup(inputs, ["execution_context", "now"])
        if op == "workato_today":
            today = _lookup(inputs, ["execution_context", "today"])
            if today not in (None, ""): return _datetime(today).date().isoformat()
            if configured not in (None, ""):
                return _datetime(configured).astimezone(timezone.utc).date().isoformat()
        elif configured not in (None, ""):
            return str(configured)
        raise ReplayResolutionError(f"{op} requires public execution context")
    if op == "workato_uuid":
        values = _lookup(inputs, ["execution_context", "workato_uuids"])
        if not isinstance(values, list) or not values: raise ReplayResolutionError("workato_uuid requires deterministic values")
        return str(values[0])
    if op == "duration":
        if len(args) != 2: raise ReplayResolutionError("duration requires value and unit")
        return {"$duration": [_integer(args[0]), str(args[1])]}
    if op == "range":
        if len(args) not in {2, 3}: raise ReplayResolutionError("range requires endpoints")
        return {"$range": [_integer(args[0]), _integer(args[1]) - (1 if len(args) == 3 and args[2] else 0)]}
    if op == "canonical_optional_integer":
        if len(args) != 1: raise ReplayResolutionError("canonical_optional_integer requires one operand")
        return None if _blank(args[0]) else _integer(args[0])
    if op == "schema_boolean":
        if len(args) != 1: raise ReplayResolutionError("schema_boolean requires one operand")
        if isinstance(args[0], str) and args[0].strip().lower() in {"true", "false"}:
            return args[0].strip().lower() == "true"
        return args[0]
    if op == "salesforce_sobject":
        if len(args) != 1: raise ReplayResolutionError("salesforce_sobject requires one query")
        match = re.search(r"\bFROM\s+([A-Za-z0-9_]+)", str(args[0] or ""), flags=re.I)
        return match.group(1) if match else ""
    if op == "get_dynamic":
        if len(args) != 2: raise ReplayResolutionError("get_dynamic requires collection and key")
        if isinstance(args[1], dict) and "$range" in args[1]:
            start, end = args[1]["$range"]; return args[0][start:end + 1]
        return _lookup(args[0], [args[1]])
    if op == "negate": return -(args[0] if args else 0)
    if op in {
        "add", "subtract", "multiply", "divide", "modulo",
        "workato_add", "workato_subtract", "workato_divide",
    }:
        if len(args) != 2: raise ReplayResolutionError(f"{op} requires two operands")
        left, right = args
        if op in {"add", "subtract", "workato_add", "workato_subtract"} and isinstance(right, dict) and "$duration" in right:
            amount, unit = right["$duration"]
            left_time = _datetime(left)
            direction = 1 if op in {"add", "workato_add"} else -1
            result = (_shift_months(left_time, direction * amount * (12 if unit == "years" else 1))
                      if unit in {"months", "years"}
                      else left_time + timedelta(**{unit: direction * amount}))
            return (result.date().isoformat()
                    if isinstance(left, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", left)
                    else result.isoformat())
        if op == "workato_add":
            if (
                isinstance(left, str)
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}", left)
                and isinstance(right, (int, float))
                and not isinstance(right, bool)
            ):
                return (
                    _datetime(left) + timedelta(days=right)
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
                return (_datetime(left) - _datetime(right)).days
            try:
                return _workato_numeric_text(float(left) - float(right))
            except (TypeError, ValueError):
                difference = _datetime(left) - _datetime(right)
                seconds = difference.total_seconds()
                return int(seconds) if seconds.is_integer() else seconds
        if op == "workato_divide":
            return _workato_numeric_text(float(left) / float(right))
        if op == "add":
            if isinstance(left, str) and isinstance(right, (int, float)):
                try:
                    return (_datetime(left) + timedelta(seconds=right)).isoformat()
                except ReplayResolutionError:
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
                difference = _datetime(left) - _datetime(right)
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
                raise ReplayResolutionError("division by zero in formula")
            dividend = _arithmetic_number(left)
            return dividend // divisor if _integer_like(left) and _integer_like(right) else dividend / divisor
        divisor = _arithmetic_number(right)
        if divisor == 0:
            raise ReplayResolutionError("modulo by zero in formula")
        return _arithmetic_number(left) % divisor
    if op == "call_method":
        if len(args) < 2: raise ReplayResolutionError("call_method requires receiver and method")
        return _method(str(args[1]), args[0], args[2:], inputs)
    if op == "call_function":
        if len(args) < 3 or args[0] != "lookup" or not isinstance(args[-1], dict):
            raise ReplayResolutionError("unsupported Workato function")
        card = resources.get(str(args[1]))
        if not isinstance(card, dict): raise ReplayResolutionError(f"lookup resource {args[1]!r} unavailable")
        rows = card.get("rows") or card.get("entries") or card.get("configured_values") or []
        matches = _where(rows, args[-1]); return matches[0] if matches else None
    if op == "slack_text":
        if len(args) != 1: raise ReplayResolutionError("slack_text requires one object")
        return _slack_text_resolved(args[0])
    if op == "slack_attachments":
        if len(args) != 1: raise ReplayResolutionError("slack_attachments requires one object")
        return _slack_attachments_resolved(args[0])
    raise ReplayResolutionError(f"unsupported expression op {op!r}")


def _resource_index(workspace_resources: Iterable[dict[str, Any]] | None) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for card in workspace_resources or []:
        if not isinstance(card, dict):
            continue
        for key in ("name", "public_id", "resource_ref", "template_ref"):
            value = str(card.get(key) or "")
            if value:
                result[value] = card
    return result


def _tool_metadata(tool_specs: Any) -> dict[str, dict[str, Any]]:
    if isinstance(tool_specs, dict) and any(
        isinstance(tool_specs.get(key), list)
        for key in ("public_tool_cards", "public_tool_surface", "tool_cards", "specs")
    ):
        tool_specs = next(
            tool_specs[key]
            for key in ("public_tool_cards", "public_tool_surface", "tool_cards", "specs")
            if isinstance(tool_specs.get(key), list)
        )
    if isinstance(tool_specs, dict):
        rows = [
            ({"name": key, **value} if isinstance(value, dict) else {"name": key})
            for key, value in tool_specs.items()
        ]
    else:
        rows = list(tool_specs or [])
    return {
        str(row.get("name") or ""): row
        for row in rows
        if isinstance(row, dict) and row.get("name")
    }


def _plan_index(
    workflow: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, str]]]]:
    nodes: dict[str, dict[str, Any]] = {}
    ancestors: dict[str, list[dict[str, str]]] = {}

    def walk(values: Iterable[dict[str, Any]], path: list[dict[str, str]]) -> None:
        for node in values:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("id") or "")
            if node_id:
                nodes[node_id] = node
                ancestors[node_id] = deepcopy(path)
            kind = str(node.get("kind") or "")
            regions: tuple[tuple[str, str], ...] = ()
            if kind == "if":
                regions = (("then", "condition_true"), ("else", "condition_false"))
            elif kind == "try":
                regions = (("body", "try_body"), ("catch", "exception"))
            elif kind == "foreach":
                regions = (("body", "loop_body"),)
            elif kind == "repeat":
                regions = (("body", "repeat_body"),)
            for key, region in regions:
                children = node.get(key)
                if isinstance(children, list):
                    walk(
                        children,
                        [*path, {"controller": node_id, "region": region}],
                    )

    walk(workflow, [])
    return nodes, ancestors


def _normal_bucket(count: int) -> str:
    return "zero" if count == 0 else "one" if count == 1 else "multiple"


def workflow_plan_variant_consistency_report(
    workflow_plan: dict[str, Any] | list[dict[str, Any]],
    *,
    active_trace: dict[str, Any],
    simulator_execution: dict[str, Any] | list[dict[str, Any]],
    public_runtime_input: dict[str, Any] | None,
    private_source_mapping: dict[str, str] | None = None,
    private_variant_state: dict[str, Any] | None = None,
    tool_specs: Any = None,
    workspace_resources: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compare one frozen-plan episode with the recipe simulator episode.

    ``simulator_execution`` is either the simulator ``output.json`` object or
    its ordered ``tool_calls`` list.  Full call results are required so later
    ``output_ref`` arguments can be resolved.  This private evidence is used
    only by the generation gate and is never published.
    """

    plan_object = workflow_plan if isinstance(workflow_plan, dict) else {}
    workflow = (
        plan_object.get("workflow")
        if isinstance(workflow_plan, dict)
        else workflow_plan
    )
    workflow = workflow if isinstance(workflow, list) else []
    plan_nodes, ancestors = _plan_index(workflow)
    plan_calls = {
        node_id: node
        for node_id, node in plan_nodes.items()
        if node.get("kind") == "call"
    }
    events = [
        event
        for event in active_trace.get("events") or []
        if isinstance(event, dict)
    ]
    active_calls = [event for event in events if event.get("event_type") == "tool_call"]
    raw_simulator_calls = (
        simulator_execution.get("tool_calls")
        if isinstance(simulator_execution, dict)
        else simulator_execution
    )
    simulator_calls = [
        call
        for call in raw_simulator_calls or []
        if isinstance(call, dict)
        and str(call.get("tool") or "")
        not in {
            "workato_genie.workflow_return_result",
            "workato_recipe_function.return_result",
        }
    ]
    metadata = _tool_metadata(tool_specs)
    inputs = _runtime_inputs(public_runtime_input)
    runtime_tokens = _provisioned_runtime_tokens(simulator_execution)
    if runtime_tokens:
        inputs = _replace_runtime_tokens(inputs, runtime_tokens)
    execution_details = (
        simulator_execution.get("details") or {}
        if isinstance(simulator_execution, dict)
        else {}
    )
    executed_trigger = execution_details.get("trigger")
    if isinstance(executed_trigger, dict):
        # Live seed harnesses provision IDs after reading the source variant,
        # so persisted public instances may still carry tokens such as
        # ``$OPP_ID`` while the authoritative raw execution records the
        # resolved caller payload. Replay must evaluate input_ref against the
        # payload that episode actually received. This evidence stays private;
        # interface closure is checked separately against the public input.
        execution_context = inputs.get("execution_context")
        inputs = deepcopy(executed_trigger)
        if isinstance(execution_context, dict):
            inputs["execution_context"] = execution_context
    resources = _resource_index(workspace_resources)
    raw_execution = (
        ((simulator_execution.get("details") or {}).get("raw_execution") or {})
        if isinstance(simulator_execution, dict)
        else {}
    )
    raw_control_trace = raw_execution.get("control_trace")
    raw_control_rows = (
        [row for row in raw_control_trace if isinstance(row, dict)]
        if isinstance(raw_control_trace, list)
        else []
    )
    raw_trace_rows = [
        row
        for row in raw_execution.get("trace") or []
        if isinstance(row, dict)
    ]
    source_to_plan = {
        str(source): str(plan)
        for plan, source in (private_source_mapping or {}).items()
        if plan and source
    }

    def raw_controller_source(row: dict[str, Any]) -> str:
        explicit = str(
            row.get("controller_source_ref")
            or row.get("controller")
            or ""
        )
        if explicit:
            return explicit
        number = row.get("number")
        if number not in (None, ""):
            return f"step_{number}"
        return str(row.get("as") or "")

    # A known call that is skipped by the selected branch has a deterministic
    # nil output in Workato's safe-navigation semantics.  Pre-register known
    # sources as nil; genuinely unknown source IDs still fail closed.
    outputs: dict[str, Any] = {node_id: None for node_id in plan_calls}
    outputs.update(
        {
            str(node.get("bind")): None
            for node in plan_calls.values()
            if node.get("bind")
        }
    )
    loops: dict[str, Any] = {}
    # Workato exposes a catch datapill as nil when its owning try completed
    # successfully. Keep known try bindings distinguishable from genuinely
    # unknown error references; an actual exception overwrites this seed.
    errors: dict[str, Any] = {
        node_id: None
        for node_id, node in plan_nodes.items()
        if node.get("kind") == "try"
    }
    output_versions: Counter[str] = Counter()
    output_histories: dict[str, list[Any]] = defaultdict(list)
    mismatches: list[dict[str, Any]] = []
    resolved_loop_items: dict[str, list[Any]] = {}
    loop_resolution_failed: set[str] = set()
    loop_call_occurrences: Counter[tuple[str, str]] = Counter()
    loop_current_iterations: dict[str, int] = {}
    call_expansion_occurrences: Counter[str] = Counter()
    call_expansion_results: dict[str, list[Any]] = defaultdict(list)

    def mismatch(code: str, **detail: Any) -> None:
        mismatches.append({"code": code, **deepcopy(detail)})

    # ActiveTrace deliberately omits recipe-local mechanics (logger/list/
    # variable helpers), while later benchmark-tool arguments may still read
    # their outputs.  The private source map plus the raw recipe trace is the
    # only authoritative bridge.  Seed a uniquely executed helper result
    # before resolving external calls; never guess which loop occurrence or
    # duplicate trace row a downstream reference meant.
    active_plan_node_ids = {
        str(event.get("plan_node_ref") or "") for event in active_calls
    }
    internal_output_rows: list[dict[str, Any]] = []

    def output_sources(value: Any) -> set[str]:
        sources: set[str] = set()
        if isinstance(value, dict):
            legacy = value.get("output_ref")
            if isinstance(legacy, dict):
                source = str(
                    legacy.get("node")
                    or legacy.get("source_node")
                    or legacy.get("binding")
                    or legacy.get("bind")
                    or ""
                )
                if source:
                    sources.add(source)
            if value.get("kind") == "output_ref":
                source = str(value.get("binding") or value.get("node") or "")
                if source:
                    sources.add(source)
            for child in value.values():
                sources.update(output_sources(child))
        elif isinstance(value, list):
            for child in value:
                sources.update(output_sources(child))
        return sources

    def contains_embedded_lookup(value: Any) -> bool:
        """Whether a symbolic value contains Workato's effectful lookup()."""

        if isinstance(value, dict):
            expression = value.get("expression")
            if isinstance(expression, dict):
                if (
                    expression.get("op") == "call_function"
                    and isinstance(expression.get("args"), list)
                    and expression["args"]
                    and expression["args"][0].get("literal") == "lookup"
                ):
                    return True
            return any(contains_embedded_lookup(child) for child in value.values())
        if isinstance(value, list):
            return any(contains_embedded_lookup(child) for child in value)
        return False

    def direct_node_values(node: dict[str, Any]) -> list[Any]:
        kind = str(node.get("kind") or "")
        if kind == "call":
            return [node.get("arguments") or {}]
        if kind == "if":
            return [node.get("condition")]
        if kind == "foreach":
            return [node.get("items"), node.get("batch_size")]
        if kind == "stop":
            return [node.get("value"), node.get("error")]
        # A try node owns child regions but has no symbolic value itself.
        return []

    # Only an internal helper whose value participates in this episode can
    # block replay. Repeated loop-local helpers naturally have several raw
    # trace rows; treating an unused one as ambiguous rejected otherwise
    # exact episodes. Compute the transitive output dependency closure from
    # active calls and executed controllers, then retain fail-closed ambiguity
    # handling for helpers whose value is actually required.
    dependency_roots = set(active_plan_node_ids)
    for event in events:
        if event.get("event_type") == "loop_boundary":
            loop_id = str(event.get("loop_plan_node_ref") or "")
            if loop_id:
                dependency_roots.add(loop_id)
        controller = str(event.get("controller_source_ref") or "")
        if controller:
            dependency_roots.add(
                controller if controller in plan_nodes else source_to_plan.get(controller, "")
            )
    required_output_node_ids: set[str] = set()
    pending = [node_id for node_id in dependency_roots if node_id in plan_nodes]
    visited: set[str] = set()
    while pending:
        dependent = pending.pop()
        if dependent in visited:
            continue
        visited.add(dependent)
        sources: set[str] = set()
        for value in direct_node_values(plan_nodes[dependent]):
            sources.update(output_sources(value))
        for source in sources:
            if source not in required_output_node_ids:
                required_output_node_ids.add(source)
                if source in plan_nodes:
                    pending.append(source)

    def raw_rows_for_source(source_ref: str) -> list[dict[str, Any]]:
        exact_fields = (
            "source_node_ref",
            "node_id",
            "source_ref",
        )
        exact = [
            row
            for row in raw_trace_rows
            if any(str(row.get(key) or "") == source_ref for key in exact_fields)
            and row.get("tool")
            and "result" in row
        ]
        if exact:
            return exact
        source_number = source_ref.removeprefix("step_")
        if not source_number.isdigit():
            return []
        return [
            row
            for row in raw_trace_rows
            if str(row.get("number") or "") == source_number
            and row.get("tool")
            and "result" in row
        ]

    for node_id, node in sorted(plan_calls.items()):
        if node_id in active_plan_node_ids:
            continue
        tool = str(node.get("tool") or "")
        effect_class = str(
            ((metadata.get(tool) or {}).get("side_effects") or {}).get("class")
            or ""
        )
        if effect_class != "recipe_local_state":
            continue
        if tool in {
            "workato_runtime.declare_variable",
            "workato_runtime.update_variables",
            "workato_runtime.declare_list",
            "workato_runtime.create_list",
            "workato_runtime.insert_to_list",
            "workato_runtime.insert_to_list_batch",
            "workato_runtime.accumulate_list_items",
        }:
            # Mutable variables are occurrence-sensitive. A final-state seed
            # would erase pagination cursors and other loop-carried values.
            # They are reconstructed from the ordered raw trace immediately
            # before each external call below.
            continue
        if node_id not in required_output_node_ids:
            continue
        source_ref = str((private_source_mapping or {}).get(node_id) or "")
        if not source_ref:
            # An unexecuted helper needs no runtime output.  If it did execute,
            # absence of lineage means there is intentionally no fallback
            # tool/name heuristic with which to associate the private result.
            continue
        candidates = raw_rows_for_source(source_ref)
        if not candidates:
            continue
        evidence = {
            "plan_node_ref": node_id,
            "controller_source_ref": source_ref,
            "tool": tool,
            "raw_trace_match_count": len(candidates),
        }
        raw_tools = {str(row.get("tool") or "") for row in candidates}
        if raw_tools != {tool}:
            mismatch(
                "internal_output_tool_mismatch",
                **evidence,
                raw_tools=sorted(raw_tools),
            )
            internal_output_rows.append(
                {**evidence, "raw_tools": sorted(raw_tools), "seeded": False}
            )
            continue
        provider_as = {
            (str(row.get("provider") or ""), str(row.get("as") or ""))
            for row in candidates
            if row.get("provider") and row.get("as")
        }
        result_available = False
        result: Any = None
        result_evidence = "simulator_raw_execution.trace"
        if len(provider_as) == 1:
            provider, source_as = next(iter(provider_as))
            provider_data = (raw_execution.get("data") or {}).get(provider)
            if isinstance(provider_data, dict) and source_as in provider_data:
                result = deepcopy(provider_data[source_as])
                result_available = True
                result_evidence = "simulator_raw_execution.data.final_provider_state"
        if not result_available and len(candidates) == 1:
            result = deepcopy(candidates[0].get("result"))
            result_available = True
        if not result_available:
            mismatch("internal_output_mapping_ambiguous", **evidence)
            internal_output_rows.append({**evidence, "seeded": False})
            continue
        outputs[node_id] = result
        output_versions[node_id] += 1
        bind = str(node.get("bind") or "")
        if bind:
            outputs[bind] = deepcopy(result)
            output_versions[bind] += 1
        internal_output_rows.append(
            {
                **evidence,
                "raw_tool": tool,
                "seeded": True,
                "evidence": f"private_source_mapping+{result_evidence}",
            }
        )

    caught_error_rows: list[dict[str, Any]] = []
    exception_try_ids: list[str] = []
    exception_sources = [
        raw_controller_source(control)
        for control in raw_control_rows
        if str(control.get("branch") or "") == "exception"
    ]
    exception_sources.extend(
        str(event.get("controller_source_ref") or "")
        for event in events
        if event.get("event_type") == "branch_decision"
        and event.get("branch") == "exception"
    )
    for source in dict.fromkeys(exception_sources):
        plan_id = source if source in plan_nodes else source_to_plan.get(source, "")
        if (plan_nodes.get(plan_id) or {}).get("kind") != "try":
            mismatch(
                "caught_error_try_unmapped",
                controller_source_ref=source,
                plan_node_ref=plan_id,
            )
            continue
        if plan_id not in exception_try_ids:
            exception_try_ids.append(plan_id)

    raw_catch = (raw_execution.get("data") or {}).get("catch")
    raw_catch_payloads = [
        (str(source), deepcopy(payload))
        for source, payload in (raw_catch or {}).items()
        if isinstance(payload, dict)
    ] if isinstance(raw_catch, dict) else []
    force_action_error = None
    for container in (
        private_variant_state or {},
        simulator_execution if isinstance(simulator_execution, dict) else {},
        (simulator_execution.get("details") or {})
        if isinstance(simulator_execution, dict)
        else {},
    ):
        candidate = container.get("force_action_error")
        if isinstance(candidate, dict):
            force_action_error = candidate
            break
    forced_message = str(
        (force_action_error or {}).get("error")
        or (force_action_error or {}).get("message")
        or ""
    )

    if len(exception_try_ids) == 1:
        try_id = exception_try_ids[0]
        payload: dict[str, Any] | None = None
        evidence = ""
        source_ref = ""
        if len(raw_catch_payloads) == 1:
            source_ref, payload = raw_catch_payloads[0]
            evidence = "simulator_raw_execution.data.catch"
            if forced_message and str(payload.get("message") or "") != forced_message:
                mismatch(
                    "caught_error_force_evidence_mismatch",
                    try_plan_node_ref=try_id,
                    raw_catch_message=payload.get("message"),
                    forced_error_message=forced_message,
                )
        elif not raw_catch_payloads and forced_message:
            payload = {
                "message": forced_message,
                "type": str(
                    (force_action_error or {}).get("type")
                    or "RawRecipeExecutionError"
                ),
            }
            evidence = "private_variant_state.force_action_error"
            source_ref = str((force_action_error or {}).get("step_as") or "")
        elif len(raw_catch_payloads) > 1:
            mismatch(
                "caught_error_payload_ambiguous",
                try_plan_node_refs=exception_try_ids,
                catch_source_refs=[source for source, _ in raw_catch_payloads],
            )
        else:
            mismatch(
                "caught_error_payload_missing",
                try_plan_node_ref=try_id,
            )
        if payload is not None:
            errors[try_id] = deepcopy(payload)
            error_bind = str((plan_nodes.get(try_id) or {}).get("error_bind") or "")
            if error_bind:
                errors[error_bind] = deepcopy(payload)
            caught_error_rows.append(
                {
                    "try_plan_node_ref": try_id,
                    "catch_source_ref": source_ref,
                    "error_bind": error_bind,
                    "payload": deepcopy(payload),
                    "evidence": evidence,
                }
            )
    elif exception_try_ids or raw_catch_payloads:
        # Without a unique executed try, associating a private exception with
        # a public error_ref would be a guess.  Modern error_bind names may
        # make multi-catch mapping explicit in a future extension.
        mismatch(
            "caught_error_mapping_ambiguous",
            try_plan_node_refs=exception_try_ids,
            catch_source_refs=[source for source, _ in raw_catch_payloads],
            has_force_action_error=bool(forced_message),
        )

    if not workflow:
        mismatch("workflow_missing")
    plan_hash = str(plan_object.get("workflow_plan_hash") or "")
    trace_plan_hash = str(active_trace.get("workflow_plan_hash") or "")
    if plan_hash and trace_plan_hash and plan_hash != trace_plan_hash:
        mismatch(
            "workflow_plan_hash_mismatch",
            workflow_plan_hash=plan_hash,
            active_trace_workflow_plan_hash=trace_plan_hash,
        )
    if len(active_calls) != len(simulator_calls):
        mismatch(
            "active_simulator_call_count_mismatch",
            active_count=len(active_calls),
            simulator_count=len(simulator_calls),
        )

    loop_item_source_versions: dict[str, tuple[tuple[str, int], ...]] = {}

    def ensure_loop_items(loop_id: str) -> list[Any] | None:
        loop_node = plan_nodes.get(loop_id) or {}
        sources = output_sources(loop_node.get("items"))
        source_versions = tuple(
            sorted((source, output_versions[source]) for source in sources)
        )
        if (
            loop_id in resolved_loop_items
            and loop_item_source_versions.get(loop_id) == source_versions
        ):
            return resolved_loop_items[loop_id]
        if loop_id in resolved_loop_items:
            # A producer ran again (commonly an outer repeat fetching the next
            # page). The nested foreach starts a new occurrence even when the
            # new page happens to contain JSON-equal rows.
            resolved_loop_items.pop(loop_id, None)
            loop_resolution_failed.discard(loop_id)
            for key in list(loop_call_occurrences):
                if key[0] == loop_id:
                    del loop_call_occurrences[key]
            loop_current_iterations.pop(loop_id, None)
        if loop_id in loop_resolution_failed:
            return None
        try:
            resolved = _resolve_value(
                loop_node.get("items"),
                inputs=inputs,
                outputs=outputs,
                loops=loops,
                errors=errors,
                resources=resources,
            )
        except ReplayResolutionError as exc:
            loop_resolution_failed.add(loop_id)
            mismatch(
                "plan_loop_items_unresolved",
                loop_plan_node_ref=loop_id,
                error=str(exc),
            )
            return None
        if resolved is None:
            resolved = []
        if not isinstance(resolved, list):
            loop_resolution_failed.add(loop_id)
            mismatch(
                "plan_loop_items_not_array",
                loop_plan_node_ref=loop_id,
                resolved_type=type(resolved).__name__,
            )
            return None
        batch_binding = loop_node.get("batch_size")
        if batch_binding is not None:
            try:
                batch_size = _integer(
                    _resolve_value(
                        batch_binding,
                        inputs=inputs,
                        outputs=outputs,
                        loops=loops,
                        errors=errors,
                        resources=resources,
                    )
                )
            except ReplayResolutionError as exc:
                loop_resolution_failed.add(loop_id)
                mismatch(
                    "plan_loop_batch_size_unresolved",
                    loop_plan_node_ref=loop_id,
                    error=str(exc),
                )
                return None
            if batch_size <= 0:
                loop_resolution_failed.add(loop_id)
                mismatch(
                    "plan_loop_batch_size_invalid",
                    loop_plan_node_ref=loop_id,
                    resolved_batch_size=batch_size,
                )
                return None
            resolved = [
                resolved[index : index + batch_size]
                for index in range(0, len(resolved), batch_size)
            ]
        resolved_loop_items[loop_id] = deepcopy(resolved)
        loop_item_source_versions[loop_id] = source_versions
        return resolved_loop_items[loop_id]

    # Reconstruct recipe-local variable state at each external-call boundary.
    # The raw executor records internal helpers in order, while ActiveTrace and
    # ``tool_calls`` intentionally omit them. Static final-state seeding is
    # therefore insufficient for repeat loops: the first page may see no
    # cursor, the second page a token, and the final state no cursor again.
    def raw_row_plan_id(row: dict[str, Any]) -> str:
        candidates = [
            str(row.get("source_node_ref") or ""),
            str(row.get("node_id") or ""),
            str(row.get("source_ref") or ""),
        ]
        if row.get("number") not in (None, ""):
            candidates.append(f"step_{row['number']}")
        candidates.append(str(row.get("as") or ""))
        for source in candidates:
            if not source:
                continue
            plan_id = source if source in plan_nodes else source_to_plan.get(source, "")
            if plan_id:
                return plan_id
        return ""

    def update_variable_lines(row: dict[str, Any]) -> set[str]:
        name = str((row.get("args") or {}).get("name") or "")
        return {
            parts[-2].strip()
            for raw_line in name.splitlines()
            if len(parts := raw_line.split(":")) >= 3 and parts[-2].strip()
        }

    variable_states: dict[str, dict[str, Any]] = {}
    list_state_plan_by_line: dict[str, str] = {}

    def apply_internal_raw_row(row: dict[str, Any]) -> None:
        tool = str(row.get("tool") or "")
        if str(
            ((metadata.get(tool) or {}).get("side_effects") or {}).get("class")
            or ""
        ) != "recipe_local_state":
            return
        plan_id = raw_row_plan_id(row)
        if not plan_id:
            return
        result = deepcopy(row.get("result"))
        if tool == "workato_runtime.declare_variable":
            line = str(row.get("as") or "")
            if line and isinstance(result, dict):
                variable_states[line] = deepcopy(result)
            outputs[plan_id] = result
            output_versions[plan_id] += 1
            bind = str((plan_nodes.get(plan_id) or {}).get("bind") or "")
            if bind:
                outputs[bind] = deepcopy(result)
                output_versions[bind] += 1
            return
        if tool in {
            "workato_runtime.declare_list",
            "workato_runtime.create_list",
        }:
            line = str(row.get("as") or "")
            if line:
                list_state_plan_by_line[line] = plan_id
            outputs[plan_id] = result
            output_versions[plan_id] += 1
            bind = str((plan_nodes.get(plan_id) or {}).get("bind") or "")
            if bind:
                outputs[bind] = deepcopy(result)
                output_versions[bind] += 1
            return
        if tool in {
            "workato_runtime.insert_to_list",
            "workato_runtime.insert_to_list_batch",
            "workato_runtime.accumulate_list_items",
        }:
            name = str((row.get("args") or {}).get("name") or "")
            line = name.rsplit(":", 1)[-1].strip() if ":" in name else ""
            owner_plan_id = list_state_plan_by_line.get(line, "")
            if owner_plan_id:
                outputs[owner_plan_id] = deepcopy(result)
                output_versions[owner_plan_id] += 1
                owner_bind = str(
                    (plan_nodes.get(owner_plan_id) or {}).get("bind") or ""
                )
                if owner_bind:
                    outputs[owner_bind] = deepcopy(result)
                    output_versions[owner_bind] += 1
            outputs[plan_id] = result
            output_versions[plan_id] += 1
            bind = str((plan_nodes.get(plan_id) or {}).get("bind") or "")
            if bind:
                outputs[bind] = deepcopy(result)
                output_versions[bind] += 1
            return
        if tool == "workato_runtime.update_variables":
            lines = update_variable_lines(row)
            merged: dict[str, Any] = {}
            if len(lines) == 1:
                line = next(iter(lines))
                merged = deepcopy(variable_states.get(line) or {})
                if isinstance(result, dict):
                    merged.update(deepcopy(result))
                variable_states[line] = deepcopy(merged)
            elif isinstance(result, dict):
                merged = deepcopy(result)
            outputs[plan_id] = merged
            output_versions[plan_id] += 1
            bind = str((plan_nodes.get(plan_id) or {}).get("bind") or "")
            if bind:
                outputs[bind] = deepcopy(merged)
                output_versions[bind] += 1
            return
        outputs[plan_id] = result
        output_histories[plan_id].append(deepcopy(result))
        output_versions[plan_id] += 1
        bind = str((plan_nodes.get(plan_id) or {}).get("bind") or "")
        if bind:
            outputs[bind] = deepcopy(result)
            output_histories[bind].append(deepcopy(result))
            output_versions[bind] += 1

    raw_call_positions: list[int | None] = []
    raw_search_start = 0
    for simulator_call in simulator_calls:
        simulator_tool = str(simulator_call.get("tool") or "")
        simulator_args = simulator_call.get("args") or {}
        same_tool_positions = [
            position
            for position in range(raw_search_start, len(raw_trace_rows))
            if str(raw_trace_rows[position].get("tool") or "") == simulator_tool
        ]
        exact_position = next(
            (
                position
                for position in same_tool_positions
                if exact_arguments_equal(
                    simulator_tool,
                    raw_trace_rows[position].get("args") or {},
                    simulator_args,
                )
            ),
            None,
        )
        position = exact_position
        if position is None and same_tool_positions:
            # Argument projection can intentionally differ between the raw
            # authoring action and canonical connector call. Tool order is
            # still unambiguous because both traces are ordered.
            position = same_tool_positions[0]
        raw_call_positions.append(position)
        if position is not None:
            raw_search_start = position + 1

    raw_timeline_cursor = 0

    call_rows: list[dict[str, Any]] = []
    for index in range(max(len(active_calls), len(simulator_calls))):
        active = active_calls[index] if index < len(active_calls) else None
        simulator = simulator_calls[index] if index < len(simulator_calls) else None
        row: dict[str, Any] = {"execution_index": index}
        if active is None or simulator is None:
            row["mapped"] = False
            call_rows.append(row)
            continue
        raw_call_position = (
            raw_call_positions[index] if index < len(raw_call_positions) else None
        )
        if raw_call_position is not None:
            for raw_row in raw_trace_rows[raw_timeline_cursor:raw_call_position]:
                apply_internal_raw_row(raw_row)
            raw_timeline_cursor = raw_call_position + 1
        node_id = str(active.get("plan_node_ref") or "")
        node = plan_calls.get(node_id)
        active_tool = str(active.get("tool") or "")
        simulator_tool = str(simulator.get("tool") or "")
        row.update(
            {
                "plan_node_ref": node_id,
                "plan_tool": str((node or {}).get("tool") or ""),
                "active_tool": active_tool,
                "simulator_tool": simulator_tool,
            }
        )
        if node is None:
            mismatch(
                "active_call_unmapped_to_plan",
                execution_index=index,
                plan_node_ref=node_id,
                active_tool=active_tool,
            )
            row["mapped"] = False
            call_rows.append(row)
            continue
        row["mapped"] = True
        plan_tool = str(node.get("tool") or "")
        embedded_expression_call = bool(
            active.get("embedded_expression_call") is True
            and active_tool == "lookup_table.get_entry"
            and contains_embedded_lookup(node.get("arguments") or {})
        )
        effective_plan_tool = active_tool if embedded_expression_call else plan_tool
        row["embedded_expression_call"] = embedded_expression_call
        row["effective_plan_tool"] = effective_plan_tool
        call_expansion = node.get("call_expansion")
        expansion_index: int | None = None
        if isinstance(call_expansion, dict):
            expansion_index = call_expansion_occurrences[node_id]
            call_expansion_occurrences[node_id] += 1
            row["call_expansion_index"] = expansion_index
        if not (effective_plan_tool == active_tool == simulator_tool):
            mismatch(
                "tool_identity_or_order_mismatch",
                execution_index=index,
                plan_node_ref=node_id,
                plan_tool=plan_tool,
                active_tool=active_tool,
                simulator_tool=simulator_tool,
            )

        row_loop_iterations: list[dict[str, Any]] = []
        loop_contexts: list[tuple[str, list[Any], int]] = []
        loop_ancestors = [
            ancestor
            for ancestor in ancestors.get(node_id, [])
            if ancestor["region"] == "loop_body"
        ]
        for ancestor_index, ancestor in enumerate(loop_ancestors):
            loop_id = ancestor["controller"]
            items = ensure_loop_items(loop_id)
            if ancestor_index < len(loop_ancestors) - 1:
                # Repeated calls in an inner loop do not advance the outer
                # foreach. Keep the outer item frozen until an outer-level
                # sibling call (or exact argument evidence) advances it.
                iteration_index = loop_current_iterations.get(loop_id, 0)
            else:
                occurrence_key = (loop_id, node_id)
                iteration_index = loop_call_occurrences[occurrence_key]
                loop_call_occurrences[occurrence_key] += 1
            if items is None:
                continue
            if iteration_index >= len(items):
                mismatch(
                    "loop_body_call_exceeds_resolved_items",
                    execution_index=index,
                    plan_node_ref=node_id,
                    loop_plan_node_ref=loop_id,
                    iteration_index=iteration_index,
                    resolved_iteration_count=len(items),
                )
                continue
            iteration_index = max(
                iteration_index,
                loop_current_iterations.get(loop_id, 0),
            )
            if iteration_index >= len(items):
                mismatch(
                    "loop_body_call_exceeds_resolved_items",
                    execution_index=index,
                    plan_node_ref=node_id,
                    loop_plan_node_ref=loop_id,
                    iteration_index=iteration_index,
                    resolved_iteration_count=len(items),
                )
                continue
            loop_contexts.append((loop_id, items, iteration_index))

        def bind_loop_item(loop_id: str, items: list[Any], iteration_index: int) -> None:
            current_item = deepcopy(items[iteration_index])
            # The deterministic compiler uses the foreach plan-node ID as the
            # producer for current-item output_ref values.  Model-normalized
            # plans may instead use item_bind/loop_ref.  Populate both forms.
            # A Workato foreach producer exposes both fields of the current
            # row and the current ``batch`` collection.  Most datapills read
            # the row directly; composite actions use
            # ``batch.current_item``/``____source = batch``.  Preserve both
            # views without changing the loop binding itself.
            loop_output = deepcopy(current_item)
            if isinstance(current_item, list):
                loop_output = {"batch": deepcopy(current_item)}
            elif isinstance(loop_output, dict) and "batch" not in loop_output:
                loop_output["batch"] = [deepcopy(current_item)]
            if isinstance(loop_output, dict):
                loop_output.setdefault("index", iteration_index)
                loop_output.setdefault("seq_no", iteration_index + 1)
                loop_output.setdefault("size", len(items))
            outputs[loop_id] = loop_output
            loops[loop_id] = deepcopy(current_item)
            item_bind = str((plan_nodes.get(loop_id) or {}).get("item_bind") or "")
            if item_bind:
                loops[item_bind] = deepcopy(current_item)

        def embedded_lookup_arguments(value: Any) -> list[dict[str, Any]]:
            candidates: list[dict[str, Any]] = []
            if isinstance(value, dict):
                expression = value.get("expression")
                if (
                    isinstance(expression, dict)
                    and expression.get("op") == "call_function"
                    and isinstance(expression.get("args"), list)
                    and len(expression["args"]) >= 3
                ):
                    resolved = [
                        _resolve_value(
                            item,
                            inputs=inputs,
                            outputs=outputs,
                            loops=loops,
                            errors=errors,
                            resources=resources,
                        )
                        for item in expression["args"]
                    ]
                    if resolved[0] == "lookup" and isinstance(resolved[-1], dict):
                        candidates.append(
                            {
                                "lookup_table_id": str(resolved[1]),
                                "parameters": resolved[-1],
                            }
                        )
                for child in value.values():
                    candidates.extend(embedded_lookup_arguments(child))
            elif isinstance(value, list):
                for child in value:
                    candidates.extend(embedded_lookup_arguments(child))
            return candidates

        def candidate_arguments() -> dict[str, Any]:
            if embedded_expression_call:
                candidates = embedded_lookup_arguments(node.get("arguments") or {})
                exact = [
                    item
                    for item in candidates
                    if exact_arguments_equal(
                        effective_plan_tool,
                        item,
                        active.get("arguments") or {},
                    )
                ]
                if len(exact) == 1:
                    return exact[0]
                if len(candidates) == 1:
                    return candidates[0]
                raise ReplayResolutionError(
                    "embedded lookup call could not be mapped uniquely"
                )
            resolved_arguments: dict[str, Any] = {}
            for key, value in (node.get("arguments") or {}).items():
                resolved = _resolve_value(
                    value,
                    inputs=inputs,
                    outputs=outputs,
                    loops=loops,
                    errors=errors,
                    resources=resources,
                )
                if resolved is not _WORKATO_SKIP:
                    resolved_arguments[str(key)] = resolved
            if isinstance(call_expansion, dict):
                collection_argument = str(
                    call_expansion.get("collection_argument") or ""
                )
                item_argument = str(call_expansion.get("item_argument") or "")
                items = resolved_arguments.pop(collection_argument, None)
                if not isinstance(items, list):
                    raise ReplayResolutionError(
                        f"call expansion argument {collection_argument!r} "
                        "did not resolve to an array"
                    )
                assert expansion_index is not None
                if expansion_index >= len(items):
                    raise ReplayResolutionError(
                        f"call expansion occurrence {expansion_index} exceeds "
                        f"{len(items)} resolved items"
                    )
                resolved_arguments[item_argument] = deepcopy(items[expansion_index])
            return resolved_arguments

        chosen_indices = [context[2] for context in loop_contexts]
        for (loop_id, items, _), iteration_index in zip(
            loop_contexts, chosen_indices
        ):
            bind_loop_item(loop_id, items, iteration_index)

        # A call node may appear only in one branch of an outer foreach. A
        # per-node occurrence counter then starts at zero even though earlier
        # sibling calls have already advanced the same loop. Keep a shared
        # monotonic cursor and, when necessary, prove the exact iteration by
        # resolving the frozen arguments against the recorded call. This is
        # evidence selection only: if no item produces the exact arguments,
        # the ordinary argument mismatch remains visible.
        if loop_contexts:
            try:
                initially_exact = exact_arguments_equal(
                    effective_plan_tool,
                    candidate_arguments(),
                    active.get("arguments") or {},
                )
            except ReplayResolutionError:
                initially_exact = False
            if not initially_exact:
                ranges = [
                    range(loop_current_iterations.get(loop_id, 0), len(items))
                    for loop_id, items, _ in loop_contexts
                ]
                combinations = 1
                for values in ranges:
                    combinations *= len(values)
                if combinations <= 4096:
                    for candidate_indices in product(*ranges):
                        for (loop_id, items, _), candidate_index in zip(
                            loop_contexts, candidate_indices
                        ):
                            bind_loop_item(loop_id, items, candidate_index)
                        try:
                            matches = exact_arguments_equal(
                                effective_plan_tool,
                                candidate_arguments(),
                                active.get("arguments") or {},
                            )
                        except ReplayResolutionError:
                            matches = False
                        if matches:
                            chosen_indices = list(candidate_indices)
                            break
                for (loop_id, items, _), iteration_index in zip(
                    loop_contexts, chosen_indices
                ):
                    bind_loop_item(loop_id, items, iteration_index)

        for (loop_id, items, _), iteration_index in zip(
            loop_contexts, chosen_indices
        ):
            loop_current_iterations[loop_id] = iteration_index
            row_loop_iterations.append(
                {
                    "loop_plan_node_ref": loop_id,
                    "iteration_index": iteration_index,
                    "resolved_iteration_count": len(items),
                    "evidence": "frozen_items_binding_and_call_occurrence",
                }
            )
        if row_loop_iterations:
            row["loop_iterations"] = row_loop_iterations

        active_arguments = active.get("arguments") or {}
        simulator_arguments = simulator.get("args") or {}
        if not exact_arguments_equal(
            active_tool, active_arguments, simulator_arguments
        ):
            mismatch(
                "active_simulator_arguments_mismatch",
                execution_index=index,
                plan_node_ref=node_id,
                active_arguments=active_arguments,
                simulator_arguments=simulator_arguments,
            )
        try:
            resolved_arguments = candidate_arguments()
            row["resolved_arguments"] = resolved_arguments
            row["canonical_resolved_arguments"] = canonical_exact_argument_view(
                effective_plan_tool, resolved_arguments
            )
            row["arguments_exact"] = exact_arguments_equal(
                effective_plan_tool, resolved_arguments, active_arguments
            )
            if not row["arguments_exact"]:
                mismatch(
                    "plan_arguments_mismatch",
                    execution_index=index,
                    plan_node_ref=node_id,
                    resolved_plan_arguments=resolved_arguments,
                    simulator_arguments=simulator_arguments,
                )
        except ReplayResolutionError as exc:
            row["arguments_exact"] = False
            row["resolution_error"] = str(exc)
            mismatch(
                "plan_arguments_unresolved",
                execution_index=index,
                plan_node_ref=node_id,
                error=str(exc),
            )

        result = deepcopy(simulator.get("result"))
        if not embedded_expression_call:
            output_value = result
            if isinstance(call_expansion, dict):
                call_expansion_results[node_id].append(deepcopy(result))
                output_value = deepcopy(call_expansion_results[node_id])
            outputs[node_id] = output_value
            output_histories[node_id].append(deepcopy(output_value))
            output_versions[node_id] += 1
            bind = str(node.get("bind") or "")
            if bind:
                outputs[bind] = deepcopy(output_value)
                output_histories[bind].append(deepcopy(output_value))
                output_versions[bind] += 1
        simulator_ok = not isinstance(result, dict) or result.get("ok", True) is True
        expected_status = str(active.get("expected_status") or "")
        if expected_status and expected_status != ("success" if simulator_ok else "error"):
            mismatch(
                "call_status_mismatch",
                execution_index=index,
                plan_node_ref=node_id,
                active_expected_status=expected_status,
                simulator_ok=simulator_ok,
            )
        call_rows.append(row)

    # Source mappings are private lineage, never model input.  They let the
    # trace's original recipe controller IDs prove which frozen control node
    # selected a branch.
    branch_events = [
        event for event in events if event.get("event_type") == "branch_decision"
    ]
    active_decision_pairs = {
        (
            str(event.get("controller_source_ref") or ""),
            str(event.get("branch") or ""),
        )
        for event in branch_events
    }
    simulator_decision_pairs: set[tuple[str, str]] = set()
    for raw_decision in raw_control_rows:
        branch = str(raw_decision.get("branch") or "")
        if branch not in {
            "condition_true", "condition_false", "try_success", "exception"
        }:
            continue
        source = raw_controller_source(raw_decision)
        controller = source if source in plan_nodes else source_to_plan.get(source, "")
        if (plan_nodes.get(controller) or {}).get("kind") not in {"if", "try"}:
            # Raw elsif/else bookkeeping can be folded into its parent by the
            # deterministic compiler and therefore has no public controller.
            continue
        simulator_decision_pairs.add((source, branch))
    if isinstance(raw_control_trace, list):
        if active_decision_pairs != simulator_decision_pairs:
            mismatch(
                "active_simulator_branch_decisions_mismatch",
                active_decisions=[list(item) for item in sorted(active_decision_pairs)],
                simulator_decisions=[
                    list(item) for item in sorted(simulator_decision_pairs)
                ],
            )
    # Some validated simulator episodes omit raw control_trace but retain the
    # derived ActiveTrace decision plus concrete catch/loop evidence.  The
    # decision is still required to map to the frozen controller below; raw
    # control rows, when present, are an additional exact comparison.

    decisions: dict[str, set[str]] = defaultdict(set)
    branch_rows: list[dict[str, Any]] = []
    for event in branch_events:
        source = str(event.get("controller_source_ref") or "")
        controller = source if source in plan_nodes else source_to_plan.get(source, "")
        branch = str(event.get("branch") or "")
        row = {
            "controller_source_ref": source,
            "plan_node_ref": controller,
            "branch": branch,
        }
        node = plan_nodes.get(controller)
        allowed = (
            {"condition_true", "condition_false"}
            if (node or {}).get("kind") == "if"
            else {"try_success", "exception"}
            if (node or {}).get("kind") == "try"
            else set()
        )
        row["mapped"] = bool(node and branch in allowed)
        if not row["mapped"]:
            mismatch("branch_decision_unmapped", **row)
        else:
            decisions[controller].add(branch)
        branch_rows.append(row)

    selected_counts = Counter(
        str(event.get("plan_node_ref") or "") for event in active_calls
    )
    for node_id, count in sorted(selected_counts.items()):
        for ancestor in ancestors.get(node_id, []):
            controller = ancestor["controller"]
            region = ancestor["region"]
            if region in {"condition_true", "condition_false"}:
                if region not in decisions.get(controller, set()):
                    mismatch(
                        "selected_call_missing_branch_evidence",
                        plan_node_ref=node_id,
                        controller_plan_node_ref=controller,
                        required_branch=region,
                        selected_count=count,
                    )
            elif region == "exception" and "exception" not in decisions.get(
                controller, set()
            ):
                mismatch(
                    "selected_catch_call_missing_exception_evidence",
                    plan_node_ref=node_id,
                    controller_plan_node_ref=controller,
                )

    for controller, selected in decisions.items():
        node = plan_nodes.get(controller) or {}
        if node.get("kind") == "if" and len(selected) > 1:
            # Both outcomes are legitimate only when the controller itself is
            # inside a loop and was evaluated for different items.
            in_loop = any(
                item["region"] in {"loop_body", "repeat_body"}
                for item in ancestors.get(controller, [])
            )
            if not in_loop:
                mismatch(
                    "non_loop_if_selected_both_branches",
                    controller_plan_node_ref=controller,
                    branches=sorted(selected),
                )

    loop_events = [
        event for event in events if event.get("event_type") == "loop_boundary"
    ]

    def control_path_reached(node_id: str) -> bool:
        for ancestor in ancestors.get(node_id, []):
            region = ancestor["region"]
            if region not in {
                "condition_true",
                "condition_false",
                "try_body",
                "exception",
            }:
                continue
            controller = ancestor["controller"]
            source = str(
                (private_source_mapping or {}).get(controller) or controller
            )
            selected = {
                branch
                for candidate_source, branch in active_decision_pairs
                if candidate_source == source
            }
            if not selected:
                continue
            required = (
                region
                if region in {"condition_true", "condition_false", "exception"}
                else "try_success"
            )
            if region == "try_body" and "exception" in selected:
                descendant_call_executed = any(
                    count > 0
                    and any(
                        item["controller"] == node_id
                        for item in ancestors.get(candidate_id, [])
                    )
                    for candidate_id, count in selected_counts.items()
                )
                if descendant_call_executed:
                    # The try eventually failed, but a selected descendant
                    # proves this earlier loop was reached before the failure.
                    continue
            if required not in selected:
                return False
        return True

    loop_rows: list[dict[str, Any]] = []
    loop_counts: dict[str, list[int]] = defaultdict(list)
    loop_event_totals = Counter(
        str(event.get("loop_plan_node_ref") or "") for event in loop_events
    )
    loop_event_occurrences: Counter[str] = Counter()
    for event in loop_events:
        node_id = str(event.get("loop_plan_node_ref") or "")
        count = event.get("iteration_count")
        bucket = str(event.get("iteration_bucket") or "")
        row = {
            "plan_node_ref": node_id,
            "iteration_count": count,
            "iteration_bucket": bucket,
        }
        if (plan_nodes.get(node_id) or {}).get("kind") != "foreach":
            mismatch("loop_boundary_unmapped", **row)
            row["mapped"] = False
        elif not isinstance(count, int) or count < 0 or bucket != _normal_bucket(count):
            mismatch("loop_boundary_inconsistent", **row)
            row["mapped"] = False
        else:
            row["mapped"] = True
            loop_counts[node_id].append(count)
            occurrence = loop_event_occurrences[node_id]
            loop_event_occurrences[node_id] += 1
            loop_node = plan_nodes.get(node_id) or {}
            item_sources = output_sources(loop_node.get("items"))
            occurrence_source = next(iter(item_sources)) if len(item_sources) == 1 else ""
            history = output_histories.get(occurrence_source) or []
            items: list[Any] | None
            if not control_path_reached(node_id):
                items = []
                row["inactive_control_path"] = True
            elif (
                occurrence_source
                and len(history) == loop_event_totals[node_id]
                and occurrence < len(history)
            ):
                # Nested foreach controllers can execute once per outer item.
                # ActiveTrace keeps one boundary for every occurrence, while
                # ``outputs`` necessarily contains only the producer's final
                # result after replay. Resolve each boundary against the
                # matching producer occurrence instead of comparing all of
                # them with that final result.
                occurrence_outputs = dict(outputs)
                occurrence_outputs[occurrence_source] = deepcopy(history[occurrence])
                try:
                    resolved = _resolve_value(
                        loop_node.get("items"),
                        inputs=inputs,
                        outputs=occurrence_outputs,
                        loops=loops,
                        errors=errors,
                        resources=resources,
                    )
                    items = list(resolved) if isinstance(resolved, (list, tuple)) else None
                    batch_binding = loop_node.get("batch_size")
                    if items is not None and batch_binding is not None:
                        batch_size = _integer(
                            _resolve_value(
                                batch_binding,
                                inputs=inputs,
                                outputs=occurrence_outputs,
                                loops=loops,
                                errors=errors,
                                resources=resources,
                            )
                        )
                        if batch_size > 0:
                            items = [
                                items[index : index + batch_size]
                                for index in range(0, len(items), batch_size)
                            ]
                except ReplayResolutionError:
                    items = None
            else:
                items = ensure_loop_items(node_id)
            row["resolved_plan_iteration_count"] = (
                len(items) if items is not None else None
            )
            if items is not None and count != len(items):
                mismatch(
                    "plan_active_loop_count_mismatch",
                    plan_node_ref=node_id,
                    resolved_plan_iteration_count=len(items),
                    active_iteration_count=count,
                )
        loop_rows.append(row)

    raw_loop_iterations = Counter(
        raw_controller_source(row)
        for row in raw_control_rows
        if str(row.get("branch") or "")
        in {"loop_body", "iteration", "repeat_body"}
    )
    plan_to_source = {
        str(plan): str(source)
        for plan, source in (private_source_mapping or {}).items()
        if plan and source
    }
    if isinstance(raw_control_trace, list):
        for row in loop_rows:
            if not row.get("mapped"):
                continue
            source = plan_to_source.get(
                str(row["plan_node_ref"]), str(row["plan_node_ref"])
            )
            # Many existing simulator recorders expose the concrete producer
            # result but omit loop_body rows from raw control_trace.  Absence
            # is not zero: the frozen items binding and ActiveTrace boundary
            # above are the authoritative, independently comparable pair.
            if source not in raw_loop_iterations:
                continue
            simulator_count = int(raw_loop_iterations[source])
            if row["iteration_count"] != simulator_count:
                mismatch(
                    "active_simulator_loop_count_mismatch",
                    plan_node_ref=row["plan_node_ref"],
                    controller_source_ref=source,
                    active_iteration_count=row["iteration_count"],
                    simulator_iteration_count=simulator_count,
                )
        evidenced_loop_sources = {
            plan_to_source.get(
                str(row.get("plan_node_ref") or ""),
                str(row.get("plan_node_ref") or ""),
            )
            for row in loop_rows
            if row.get("mapped")
        }
        for source, count in sorted(raw_loop_iterations.items()):
            if source not in evidenced_loop_sources:
                mismatch(
                    "simulator_loop_missing_active_boundary",
                    controller_source_ref=source,
                    simulator_iteration_count=count,
                )
    # No raw loop trace is required when the frozen items binding resolves and
    # agrees with the independently recorded ActiveTrace boundary.  Several
    # canonical simulator recorders expose exactly that evidence combination.

    for node_id in selected_counts:
        for ancestor in ancestors.get(node_id, []):
            if ancestor["region"] != "loop_body":
                continue
            controller = ancestor["controller"]
            if not any(count > 0 for count in loop_counts.get(controller, [])):
                mismatch(
                    "selected_loop_call_missing_boundary_evidence",
                    plan_node_ref=node_id,
                    loop_plan_node_ref=controller,
                )

    # For a simple unconditional body call, exact recipe execution invokes it
    # once per item.  Conditional or nested-loop calls are checked by their
    # own branch/loop evidence instead of this one-call-per-item invariant.
    for loop_id, items in sorted(resolved_loop_items.items()):
        if loop_counts.get(loop_id) and not any(loop_counts[loop_id]):
            continue
        failed_try_ancestor = any(
            ancestor["region"] == "try_body"
            and "exception" in decisions.get(ancestor["controller"], set())
            for ancestor in ancestors.get(loop_id, [])
        )
        if failed_try_ancestor:
            # A caught exception can abort the current loop before its
            # unconditional body call records a successful connector event.
            # Source cardinality remains valid loop evidence, but it does not
            # imply that every iteration completed.
            continue
        loop_node = plan_nodes.get(loop_id) or {}

        def contains_stop(values: Any) -> bool:
            if isinstance(values, dict):
                if values.get("kind") == "stop":
                    return True
                return any(contains_stop(child) for child in values.values())
            if isinstance(values, list):
                return any(contains_stop(child) for child in values)
            return False

        if contains_stop(loop_node.get("body") or []):
            # A conditional stop can terminate the foreach after any item.
            # The boundary still proves source cardinality, but source size
            # cannot imply one successful body call per item.
            continue
        for node_id in sorted(plan_calls):
            tool = str(plan_calls[node_id].get("tool") or "")
            if str(
                ((metadata.get(tool) or {}).get("side_effects") or {}).get("class")
                or ""
            ) == "recipe_local_state":
                # ActiveTrace intentionally contains benchmark tool calls,
                # not recipe-internal list/logger mechanics.  Their loop
                # execution is witnessed by the resolved collection and the
                # boundary count, but they cannot be required to appear as
                # selected tool events.
                continue
            path = ancestors.get(node_id, [])
            try:
                loop_position = next(
                    index
                    for index, ancestor in enumerate(path)
                    if ancestor["controller"] == loop_id
                    and ancestor["region"] == "loop_body"
                )
            except StopIteration:
                continue
            nested_regions = path[loop_position + 1 :]
            conditional_or_nested = any(
                ancestor["region"]
                in {
                    "condition_true",
                    "condition_false",
                    "try_body",
                    "exception",
                    "loop_body",
                }
                for ancestor in nested_regions
            )
            occurrence_count = loop_call_occurrences[(loop_id, node_id)]
            if not conditional_or_nested and occurrence_count != len(items):
                mismatch(
                    "unconditional_loop_call_count_mismatch",
                    loop_plan_node_ref=loop_id,
                    plan_node_ref=node_id,
                    resolved_iteration_count=len(items),
                    selected_call_count=occurrence_count,
                )

    terminal_events = [event for event in events if event.get("event_type") == "terminal"]
    terminal_rows = deepcopy(terminal_events)
    if len(terminal_events) != 1:
        mismatch("terminal_evidence_count_mismatch", count=len(terminal_events))
    terminal_type = str((terminal_events[0] if terminal_events else {}).get("terminal_type") or "")
    ground_truth = (
        (simulator_execution.get("details") or {}).get("ground_truth")
        if isinstance(simulator_execution, dict)
        else None
    )
    simulator_terminal_type = ""
    if isinstance(ground_truth, dict) and "return_value" in ground_truth:
        simulator_terminal_type = (
            "return" if ground_truth.get("return_value") is not None else "fallthrough"
        )
        if terminal_type != simulator_terminal_type:
            mismatch(
                "active_simulator_terminal_mismatch",
                active_terminal_type=terminal_type,
                simulator_terminal_type=simulator_terminal_type,
            )
    terminal_tools = set(INHERENTLY_TERMINAL_TOOLS)
    terminal_tools.update(
        tool
        for tool, spec in metadata.items()
        if (spec.get("side_effects") or {}).get("terminal_on_success") is True
    )
    selected_terminal_calls = [
        row for row in call_rows if row.get("active_tool") in terminal_tools
    ]
    reply_call_is_return = bool(
        terminal_type == "return"
        and isinstance(ground_truth, dict)
        and any(
            row.get("active_tool") == "workato_service.send_reply"
            and ground_truth.get("return_value")
            == active_calls[int(row["execution_index"])].get("arguments")
            for row in call_rows
            if row.get("execution_index") is not None
            and int(row["execution_index"]) < len(active_calls)
        )
    )
    has_structural_terminal = any(
        node.get("kind") in {"return", "stop"} for node in plan_nodes.values()
    )
    if (
        terminal_type == "return"
        and not selected_terminal_calls
        and not has_structural_terminal
        and not reply_call_is_return
    ):
        mismatch("terminal_return_has_no_plan_evidence")
    if terminal_type == "fallthrough" and selected_terminal_calls:
        mismatch(
            "fallthrough_after_terminal_tool",
            terminal_tools=[row.get("active_tool") for row in selected_terminal_calls],
        )
    if selected_terminal_calls:
        last_terminal_index = int(selected_terminal_calls[-1]["execution_index"])
        if last_terminal_index != len(active_calls) - 1:
            mismatch(
                "tool_call_after_terminal",
                terminal_execution_index=last_terminal_index,
                final_execution_index=len(active_calls) - 1,
            )

    side_effect_rows: list[dict[str, Any]] = []
    for row in call_rows:
        tool = str(row.get("active_tool") or "")
        if not tool:
            continue
        effect_class = str(
            ((metadata.get(tool) or {}).get("side_effects") or {}).get("class")
            or ""
        )
        side_effect_rows.append(
            {
                "execution_index": row["execution_index"],
                "plan_node_ref": row.get("plan_node_ref"),
                "tool": tool,
                "side_effect_class": effect_class,
            }
        )
        if not effect_class:
            mismatch(
                "side_effect_class_missing",
                execution_index=row["execution_index"],
                tool=tool,
            )

    active_tools = [str(event.get("tool") or "") for event in active_calls]
    simulator_tools = [str(call.get("tool") or "") for call in simulator_calls]
    selected_plan_tools = [
        str(row.get("effective_plan_tool") or row.get("plan_tool") or "")
        for row in call_rows
    ]
    checks = {
        "call_count_exact": (
            len(active_calls) == len(simulator_calls) == len(call_rows)
        ),
        "tool_identity_order_exact": (
            active_tools == simulator_tools == selected_plan_tools
        ),
        "arguments_exact": not any(
            item["code"] in {
                "active_simulator_arguments_mismatch",
                "plan_arguments_mismatch",
                "plan_arguments_unresolved",
            }
            for item in mismatches
        ),
        "branch_evidence_consistent": not any(
            "branch" in item["code"]
            or "catch" in item["code"]
            or (
                item["code"] == "simulator_control_trace_missing"
                and item.get("evidence") == "branch_decisions"
            )
            for item in mismatches
        ),
        "loop_evidence_consistent": not any(
            "loop" in item["code"]
            or (
                item["code"] == "simulator_control_trace_missing"
                and item.get("evidence") == "loop_boundaries"
            )
            for item in mismatches
        ),
        "terminal_evidence_consistent": not any(
            "terminal" in item["code"] or item["code"] == "tool_call_after_terminal"
            for item in mismatches
        ),
        "side_effects_classified": not any(
            item["code"] == "side_effect_class_missing" for item in mismatches
        ),
    }
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "recipe_id": str(active_trace.get("recipe_id") or plan_object.get("recipe_id") or ""),
        "variant_id": str(active_trace.get("variant_id") or ""),
        "workflow_plan_hash": str(
            active_trace.get("workflow_plan_hash")
            or plan_object.get("workflow_plan_hash")
            or ""
        ),
        "passed": not mismatches and all(checks.values()),
        "checks": checks,
        "selected_call_count": len(active_calls),
        "selected_plan_tool_sequence": selected_plan_tools,
        "active_trace_tool_sequence": active_tools,
        "simulator_tool_sequence": simulator_tools,
        "call_argument_parity": call_rows,
        "internal_output_evidence": internal_output_rows,
        "branch_decisions": branch_rows,
        "simulator_branch_decisions": [
            {
                "controller_source_ref": controller,
                "branch": branch,
            }
            for controller, branch in sorted(simulator_decision_pairs)
        ],
        "caught_error_evidence": caught_error_rows,
        "loop_evidence": loop_rows,
        "simulator_loop_iterations": dict(sorted(raw_loop_iterations.items())),
        "terminal_evidence": {
            "active_trace": terminal_rows,
            "simulator_terminal_type": simulator_terminal_type,
        },
        "side_effect_execution": side_effect_rows,
        "mismatches": mismatches,
    }
    report["report_hash"] = stable_json_hash(report)
    return report
