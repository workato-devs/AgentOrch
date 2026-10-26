"""Deterministic projection of Workato formula values into symbolic ASTs.

Workato stores formulas as Ruby-like strings prefixed with ``=``.  Treating
those strings as literals loses every datapill nested in the formula and, more
importantly, turns an executable recipe argument into an opaque private
expression.  This module parses the deliberately small, deterministic subset
used by the benchmark corpus.  Unknown syntax and unknown methods fail closed;
the compiler must never guess or publish an unevaluable formula string.

The returned values use the legacy one-key symbolic spelling accepted by both
the WorkflowPlan normalizer and the private replay checker.  References are
resolved by the caller because only the recipe compiler knows the mapping from
Workato ``as`` identifiers to stable plan-node identifiers.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Callable


class WorkatoFormulaError(ValueError):
    """A Workato formula cannot be projected without inventing semantics."""


ReferenceResolver = Callable[[dict[str, Any]], dict[str, Any]]

_FORMULA_REFERENCE_RE = re.compile(
    r"(?P<kind>_dp|_)\('(?P<payload>(?:\\.|[^'])*)'"
    r"(?:\s*,\s*'(?:\\.|[^'])*')*\)"
)


_METHODS = {
    "ago",
    "beginning_of_day",
    "blank?",
    "capitalize",
    "compact",
    "concat",
    "downcase",
    "ends_with?",
    "first",
    "format_map",
    "gsub",
    "include?",
    "in_time_zone",
    "is_not_true?",
    "is_true?",
    "join",
    "keys",
    "last",
    "length",
    "lstrip",
    "match?",
    "max",
    "min",
    "pluck",
    "presence",
    "present?",
    "quote",
    "reverse",
    "slice",
    "smart_join",
    "size",
    "split",
    "starts_with?",
    "strftime",
    "strip",
    "strip_tags",
    "sum",
    "titleize",
    "to_currency",
    "to_csv",
    "to_date",
    "to_f",
    "to_i",
    "to_json",
    "to_s",
    "to_time",
    "uniq",
    "unicode_normalize",
    "upcase",
    "utc",
    "where",
    "wday",
    "yweek",
}
_FUNCTIONS = {"lookup"}
_DURATION_UNITS = {
    "seconds",
    "minutes",
    "hours",
    "days",
    "weeks",
    "months",
    "years",
}


def _literal(value: Any) -> dict[str, Any]:
    return {"literal": value}


def _expression(op: str, *args: dict[str, Any]) -> dict[str, Any]:
    return {"expression": {"op": op, "args": list(args)}}


def _runtime_formula_result(value: dict[str, Any]) -> dict[str, Any]:
    """Apply Workato's direct-dispatch arithmetic semantics at a boundary.

    Top-level numeric ``+``, ``-`` and ``/`` formulas use Workato's legacy
    dispatcher, which serializes numeric results as text. The same ``-``
    dispatcher returns a numeric duration for time operands. Arithmetic nested
    under a method call stays on the typed general-expression path (for
    example ``(... / ...).to_i`` or ``(time + seconds).in_time_zone``).
    """

    expression = value.get("expression") if isinstance(value, dict) else None
    if not isinstance(expression, dict):
        return value
    legacy_op = {
        "add": "workato_add",
        "subtract": "workato_subtract",
        "divide": "workato_divide",
    }.get(str(expression.get("op") or ""))
    if not legacy_op:
        return value
    return {"expression": {**expression, "op": legacy_op}}


def _typed_formula_results(value: Any) -> Any:
    """Undo legacy boundary coercion for the typed ``_('data...')`` dialect."""

    if isinstance(value, list):
        return [_typed_formula_results(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: _typed_formula_results(item) for key, item in value.items()}
    expression = result.get("expression")
    if isinstance(expression, dict):
        expression["op"] = {
            "workato_add": "add",
            "workato_subtract": "subtract",
            "workato_divide": "divide",
        }.get(str(expression.get("op") or ""), expression.get("op"))
    return result


def _call_method(
    receiver: dict[str, Any], method: str, args: list[dict[str, Any]]
) -> dict[str, Any]:
    if method not in _METHODS:
        raise WorkatoFormulaError(f"unsupported Workato formula method {method!r}")
    return _expression("call_method", receiver, _literal(method), *args)


@dataclass(frozen=True)
class _Token:
    kind: str
    value: Any
    offset: int


class _Tokenizer:
    def __init__(self, text: str, reference_resolver: ReferenceResolver) -> None:
        self.text = text
        self.reference_resolver = reference_resolver
        self.offset = 0

    def tokens(self) -> list[_Token]:
        result: list[_Token] = []
        while self.offset < len(self.text):
            char = self.text[self.offset]
            if char.isspace():
                self.offset += 1
                continue
            if char == "#":
                # Outside a quoted string, Workato/Ruby comments consume the
                # remainder of the formula line.
                while self.offset < len(self.text) and self.text[self.offset] != "\n":
                    self.offset += 1
                continue
            if self.text.startswith("_dp(", self.offset) or self.text.startswith("_(", self.offset):
                result.append(self._reference())
                continue
            if char in {"'", '"'}:
                result.append(self._string())
                continue
            if char.isdigit():
                result.append(self._number())
                continue
            if char.isalpha() or char == "_":
                result.append(self._identifier())
                continue
            two = self.text[self.offset : self.offset + 2]
            three = self.text[self.offset : self.offset + 3]
            if three == "===":
                result.append(_Token("OP", "==", self.offset))
                self.offset += 3
                continue
            if three == "...":
                result.append(_Token("RANGE_EXCLUSIVE", three, self.offset))
                self.offset += 3
                continue
            if two == "..":
                result.append(_Token("RANGE", two, self.offset))
                self.offset += 2
                continue
            if two == "=>":
                result.append(_Token("OP", two, self.offset))
                self.offset += 2
                continue
            if two in {"&.", "==", "!=", ">=", "<=", "||", "&&"}:
                result.append(_Token("OP", two, self.offset))
                self.offset += 2
                continue
            if char == "/" and self._regex_is_possible(result):
                result.append(self._regex())
                continue
            if char in "+-*/%<>":
                result.append(_Token("OP", char, self.offset))
                self.offset += 1
                continue
            if char in "()[]{}.,?:":
                result.append(_Token(char, char, self.offset))
                self.offset += 1
                continue
            raise WorkatoFormulaError(
                f"unsupported character {char!r} at formula offset {self.offset}"
            )
        result.append(_Token("EOF", None, len(self.text)))
        return result

    def _scan_quoted(self, quote: str) -> tuple[str, int]:
        start = self.offset
        self.offset += 1
        chars: list[str] = []
        while self.offset < len(self.text):
            char = self.text[self.offset]
            if quote == '"' and self.text.startswith("#{", self.offset):
                interpolation_start = self.offset
                self.offset += 2
                depth = 1
                inner_quote: str | None = None
                while self.offset < len(self.text) and depth:
                    nested = self.text[self.offset]
                    if inner_quote:
                        if nested == "\\":
                            self.offset += 2
                            continue
                        if nested == inner_quote:
                            inner_quote = None
                    elif nested in {"'", '"'}:
                        inner_quote = nested
                    elif nested == "{":
                        depth += 1
                    elif nested == "}":
                        depth -= 1
                    self.offset += 1
                if depth:
                    raise WorkatoFormulaError(
                        f"unterminated interpolation at offset {interpolation_start}"
                    )
                chars.append(self.text[interpolation_start:self.offset])
                continue
            if char == "\\":
                if self.offset + 1 >= len(self.text):
                    raise WorkatoFormulaError("unterminated formula escape")
                chars.extend((char, self.text[self.offset + 1]))
                self.offset += 2
                continue
            if char == quote:
                self.offset += 1
                raw = "".join(chars)
                try:
                    # JSON decoding gives Workato's double-quoted escape
                    # behavior.  Single-quoted formulas only need the two Ruby
                    # escapes that occur in the corpus.
                    if quote == '"' and "#{" not in raw:
                        escapes = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\"}
                        value = re.sub(
                            r"\\(.)",
                            lambda match: escapes.get(match.group(1), match.group(1)),
                            raw,
                        )
                    elif quote == '"':
                        # Quotes inside ``#{...}`` belong to the nested Ruby
                        # expression and cannot be decoded as one JSON string.
                        # Preserve them for the recursive expression parser;
                        # decode only the ordinary outer-string escapes.
                        value = (
                            raw.replace("\\n", "\n")
                            .replace("\\r", "\r")
                            .replace("\\t", "\t")
                            .replace('\\"', '"')
                            .replace("\\\\", "\\")
                        )
                    else:
                        value = raw.replace("\\'", "'").replace("\\\\", "\\")
                except json.JSONDecodeError as exc:
                    raise WorkatoFormulaError(
                        f"invalid formula string at offset {start}: {exc}"
                    ) from exc
                return value, start
            chars.append(char)
            self.offset += 1
        raise WorkatoFormulaError(f"unterminated formula string at offset {start}")

    def _string(self) -> _Token:
        quote = self.text[self.offset]
        value, start = self._scan_quoted(quote)
        kind = "DSTRING" if quote == '"' and "#{" in value else "STRING"
        return _Token(kind, value, start)

    def _number(self) -> _Token:
        start = self.offset
        match = re.match(r"\d+(?:\.\d+)?", self.text[start:])
        assert match is not None
        raw = match.group(0)
        self.offset += len(raw)
        return _Token("NUMBER", float(raw) if "." in raw else int(raw), start)

    def _identifier(self) -> _Token:
        start = self.offset
        match = re.match(r"[A-Za-z_][A-Za-z0-9_]*(?:[?!])?", self.text[start:])
        assert match is not None
        value = match.group(0)
        self.offset += len(value)
        return _Token("IDENT", value, start)

    def _reference(self) -> _Token:
        start = self.offset
        datapill = self.text.startswith("_dp(", start)
        self.offset += 4 if datapill else 2
        while self.offset < len(self.text) and self.text[self.offset].isspace():
            self.offset += 1
        if self.offset >= len(self.text) or self.text[self.offset] not in {"'", '"'}:
            raise WorkatoFormulaError(f"reference at offset {start} has no quoted payload")
        payload, _ = self._scan_quoted(self.text[self.offset])
        # Ignore the optional Workato list-meta hints after the first data path;
        # the path itself already contains first/current-item/size semantics.
        depth = 1
        while self.offset < len(self.text) and depth:
            char = self.text[self.offset]
            if char in {"'", '"'}:
                self._scan_quoted(char)
                continue
            depth += char == "("
            depth -= char == ")"
            self.offset += 1
        if depth:
            raise WorkatoFormulaError(f"unterminated reference at offset {start}")
        if datapill:
            try:
                decoded = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise WorkatoFormulaError(
                    f"invalid _dp payload at offset {start}: {exc}"
                ) from exc
            if not isinstance(decoded, dict):
                raise WorkatoFormulaError(f"non-object _dp payload at offset {start}")
            reference = decoded
        else:
            if not isinstance(payload, str) or not payload.startswith("data."):
                raise WorkatoFormulaError(
                    f"unsupported Workato data reference {payload!r}"
                )
            parts = payload[5:].split(".")
            if len(parts) < 2:
                raise WorkatoFormulaError(f"incomplete Workato data reference {payload!r}")
            reference = {
                "pill_type": "job_context" if parts[:2] == ["workato", "job_context"] else "output",
                "provider": parts[0],
                "line": parts[1],
                "path": parts[2:],
            }
        return _Token("REFERENCE", self.reference_resolver(reference), start)

    def _regex_is_possible(self, tokens: list[_Token]) -> bool:
        if not tokens:
            return True
        previous = tokens[-1]
        return previous.kind in {"(", "[", "{", ",", ":", "OP"}

    def _regex(self) -> _Token:
        start = self.offset
        self.offset += 1
        chars: list[str] = []
        while self.offset < len(self.text):
            char = self.text[self.offset]
            if char == "\\" and self.offset + 1 < len(self.text):
                chars.extend((char, self.text[self.offset + 1]))
                self.offset += 2
                continue
            if char == "/":
                self.offset += 1
                flags: list[str] = []
                while self.offset < len(self.text) and self.text[self.offset].isalpha():
                    flags.append(self.text[self.offset])
                    self.offset += 1
                return _Token(
                    "REGEX", {"pattern": "".join(chars), "flags": "".join(flags)}, start
                )
            chars.append(char)
            self.offset += 1
        raise WorkatoFormulaError(f"unterminated regex at offset {start}")


class _Parser:
    _PRECEDENCE = {
        "or": 1,
        "||": 1,
        "and": 2,
        "&&": 2,
        "==": 3,
        "!=": 3,
        ">": 3,
        ">=": 3,
        "<": 3,
        "<=": 3,
        "+": 4,
        "-": 4,
        "*": 5,
        "/": 5,
        "%": 5,
    }
    _BINARY_OP = {
        "or": "ruby_or",
        "||": "ruby_or",
        "and": "and",
        "&&": "and",
        "==": "eq",
        "!=": "ne",
        ">": "gt",
        ">=": "gte",
        "<": "lt",
        "<=": "lte",
        "+": "add",
        "-": "subtract",
        "*": "multiply",
        "/": "divide",
        "%": "modulo",
    }

    def __init__(
        self, text: str, reference_resolver: ReferenceResolver
    ) -> None:
        self.reference_resolver = reference_resolver
        self.tokens = _Tokenizer(text, reference_resolver).tokens()
        self.index = 0

    @property
    def current(self) -> _Token:
        return self.tokens[self.index]

    def advance(self) -> _Token:
        token = self.current
        self.index += 1
        return token

    def accept(self, kind: str, value: Any | None = None) -> _Token | None:
        if self.current.kind != kind:
            return None
        if value is not None and self.current.value != value:
            return None
        return self.advance()

    def require(self, kind: str, value: Any | None = None) -> _Token:
        token = self.accept(kind, value)
        if token is None:
            expected = kind if value is None else repr(value)
            raise WorkatoFormulaError(
                f"expected {expected} at formula offset {self.current.offset}"
            )
        return token

    def parse(self) -> dict[str, Any]:
        result = self.expression()
        self.require("EOF")
        return result

    def expression(self, minimum: int = 0) -> dict[str, Any]:
        left = self.prefix()
        while True:
            operator = self._operator()
            precedence = self._PRECEDENCE.get(operator or "", -1)
            if precedence < minimum:
                break
            self.advance()
            right = self.expression(precedence + 1)
            left = _expression(self._BINARY_OP[operator], left, right)
        if minimum == 0 and self.accept("?"):
            positive = _runtime_formula_result(self.expression())
            self.require(":")
            negative = _runtime_formula_result(self.expression())
            left = {
                "expression": {
                    "op": "if",
                    "condition": left,
                    "args": [positive, negative],
                }
            }
        return left

    def _operator(self) -> str | None:
        if self.current.kind == "OP":
            return str(self.current.value)
        if self.current.kind == "IDENT" and self.current.value in {"or", "and"}:
            return str(self.current.value)
        return None

    def prefix(self) -> dict[str, Any]:
        if self.accept("OP", "-"):
            return _expression("negate", self.prefix())
        if self.current.kind == "IDENT" and self.current.value in {"not"}:
            self.advance()
            return _expression("not", self.prefix())
        result = self.primary()
        while True:
            if self.accept(".") or self.accept("OP", "&."):
                method = str(self.require("IDENT").value)
                args = self.arguments() if self.current.kind == "(" else []
                if method in _DURATION_UNITS and not args:
                    result = _expression("duration", result, _literal(method))
                else:
                    result = _call_method(result, method, args)
                continue
            if self.accept("["):
                index = self.expression()
                if self.accept(","):
                    length = self.expression()
                    self.require("]")
                    result = _call_method(result, "slice", [index, length])
                    continue
                if self.accept("RANGE_EXCLUSIVE"):
                    end = self.expression()
                    index = _expression("range", index, end, _literal(True))
                elif self.accept("RANGE"):
                    end = self.expression()
                    index = _expression("range", index, end, _literal(False))
                self.require("]")
                result = _expression("get_dynamic", result, index)
                continue
            break
        return result

    def primary(self) -> dict[str, Any]:
        token = self.advance()
        if token.kind == "REFERENCE":
            return token.value
        if token.kind == "STRING":
            return _literal(token.value)
        if token.kind == "DSTRING":
            return self._interpolated_string(str(token.value))
        if token.kind == "NUMBER":
            return _literal(token.value)
        if token.kind == "REGEX":
            return _literal({"$regex": token.value})
        if token.kind == "(":
            result = self.expression()
            self.require(")")
            return result
        if token.kind == "[":
            values: list[dict[str, Any]] = []
            if not self.accept("]"):
                while True:
                    values.append(self.expression())
                    if self.accept("]"):
                        break
                    self.require(",")
            return {"expression": {"op": "array", "items": values}}
        if token.kind == "{":
            fields: dict[str, dict[str, Any]] = {}
            if not self.accept("}"):
                while True:
                    key_token = self.advance()
                    if key_token.kind not in {"STRING", "IDENT"}:
                        raise WorkatoFormulaError(
                            f"object key at offset {key_token.offset} must be a string"
                        )
                    if not (self.accept("OP", "=>") or self.accept(":")):
                        raise WorkatoFormulaError(
                            f"object key at offset {key_token.offset} has no separator"
                        )
                    fields[str(key_token.value)] = self.expression()
                    if self.accept("}"):
                        break
                    self.require(",")
            return {"expression": {"op": "object", "fields": fields}}
        if token.kind == ":":
            return _literal(str(self.require("IDENT").value))
        if token.kind != "IDENT":
            raise WorkatoFormulaError(
                f"unexpected token {token.kind!r} at formula offset {token.offset}"
            )
        name = str(token.value)
        if name in {"nil", "null", "blank"}:
            return _literal(None)
        if name in {"true", "false"}:
            return _literal(name == "true")
        if name in {"skip", "clear", "now", "today"}:
            return {"expression": {"op": f"workato_{name}"}}
        if (
            name == "workato"
            and self.accept(".")
            and self.require("IDENT").value == "uuid"
        ):
            return {"expression": {"op": "workato_uuid"}}
        if name in _FUNCTIONS and self.current.kind == "(":
            return _expression("call_function", _literal(name), *self.arguments())
        # Ruby symbols only occur as method arguments (``pluck(:id)``).
        raise WorkatoFormulaError(
            f"unsupported formula identifier {name!r} at offset {token.offset}"
        )

    def arguments(self) -> list[dict[str, Any]]:
        self.require("(")
        positional: list[dict[str, Any]] = []
        named: dict[str, dict[str, Any]] = {}
        if self.accept(")"):
            return positional
        while True:
            if self.accept(":"):
                key = str(self.require("IDENT").value)
                value = _literal(key)
            elif (
                self.current.kind in {"STRING", "IDENT"}
                and self.tokens[self.index + 1].kind == ":"
            ):
                key = str(self.advance().value)
                self.require(":")
                named[key] = self.expression()
                value = None
            else:
                value = self.expression()
                if self.accept("OP", "=>"):
                    raw_key = value.get("literal") if set(value) == {"literal"} else None
                    if not isinstance(raw_key, str):
                        raise WorkatoFormulaError("hash-pair key must be a string literal")
                    named[raw_key] = self.expression()
                    value = None
            if value is not None:
                positional.append(value)
            if self.accept(")"):
                break
            self.require(",")
        if named:
            positional.append({"expression": {"op": "object", "fields": named}})
        return positional

    def _interpolated_string(self, value: str) -> dict[str, Any]:
        parts: list[dict[str, Any]] = []
        cursor = 0
        while True:
            start = value.find("#{", cursor)
            if start < 0:
                if cursor < len(value):
                    parts.append(_literal(value[cursor:]))
                break
            if start > cursor:
                parts.append(_literal(value[cursor:start]))
            depth = 1
            offset = start + 2
            quote: str | None = None
            while offset < len(value) and depth:
                char = value[offset]
                if quote:
                    if char == "\\":
                        offset += 2
                        continue
                    if char == quote:
                        quote = None
                elif char in {"'", '"'}:
                    quote = char
                elif char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                offset += 1
            if depth:
                raise WorkatoFormulaError("unterminated formula interpolation")
            body = value[start + 2 : offset - 1]
            parts.append(_Parser(body, self.reference_resolver).parse())
            cursor = offset
        if len(parts) == 1:
            return parts[0]
        return {"expression": {"op": "interpolate", "parts": parts}}


def _project_if_formula(
    text: str, reference_resolver: ReferenceResolver
) -> dict[str, Any] | None:
    """Project Workato's line-oriented ``if/elsif/else/end`` expression."""

    stripped = text.strip()
    lines = stripped.splitlines()
    if (
        len(lines) < 3
        or not lines[0].strip().startswith("if ")
        or lines[-1].strip() != "end"
    ):
        return None
    def meaningful(index: int) -> int:
        while index < len(lines):
            line = lines[index].strip()
            if line and not line.startswith("#"):
                return index
            index += 1
        return index

    def parse_value(index: int) -> tuple[dict[str, Any], int]:
        index = meaningful(index)
        if index >= len(lines):
            raise WorkatoFormulaError("if formula has an empty branch")
        if lines[index].strip().startswith("if "):
            return parse_if(index)
        value_lines: list[str] = []
        while index < len(lines):
            line = lines[index].strip()
            if line == "end" or line == "else" or line.startswith("else ") or line.startswith("elsif "):
                break
            if line and not line.startswith("#"):
                value_lines.append(lines[index].strip())
            index += 1
        if not value_lines:
            raise WorkatoFormulaError("if formula has an empty branch")
        return _runtime_formula_result(
            _Parser("\n".join(value_lines), reference_resolver).parse()
        ), index

    def parse_if(index: int) -> tuple[dict[str, Any], int]:
        header = lines[index].strip()
        if not header.startswith("if "):
            raise WorkatoFormulaError(f"expected nested if on line {index + 1}")
        branches: list[tuple[str, dict[str, Any]]] = []
        condition = header[3:].strip()
        index += 1
        value, index = parse_value(index)
        branches.append((condition, value))
        fallback: dict[str, Any] = _literal(None)
        while index < len(lines):
            index = meaningful(index)
            marker = lines[index].strip()
            if marker.startswith("elsif "):
                condition = marker[6:].strip()
                value, index = parse_value(index + 1)
                branches.append((condition, value))
                continue
            if marker == "else" or marker.startswith("else "):
                if marker.startswith("else "):
                    fallback = _runtime_formula_result(
                        _Parser(marker[5:].strip(), reference_resolver).parse()
                    )
                    index += 1
                else:
                    fallback, index = parse_value(index + 1)
                index = meaningful(index)
                if index >= len(lines) or lines[index].strip() != "end":
                    raise WorkatoFormulaError("if fallback is not terminated by end")
                index += 1
                break
            if marker == "end":
                index += 1
                break
            raise WorkatoFormulaError(f"unexpected if marker {marker!r}")
        result = fallback
        for branch_condition, branch_value in reversed(branches):
            result = {
                "expression": {
                    "op": "if",
                    "condition": _Parser(branch_condition, reference_resolver).parse(),
                    "args": [branch_value, result],
                }
            }
        return result, index

    result, next_index = parse_if(0)
    if meaningful(next_index) != len(lines):
        raise WorkatoFormulaError("trailing content after if formula")
    return result


def _project_template_text(
    text: str, reference_resolver: ReferenceResolver
) -> dict[str, Any]:
    """Project literal message text containing Workato ``#{...}`` pills."""

    parts: list[dict[str, Any]] = []
    cursor = 0
    while True:
        start = text.find("#{", cursor)
        if start < 0:
            if cursor < len(text):
                parts.append(_literal(text[cursor:]))
            break
        if start > cursor:
            parts.append(_literal(text[cursor:start]))
        depth = 1
        offset = start + 2
        quote: str | None = None
        while offset < len(text) and depth:
            char = text[offset]
            if quote:
                if char == "\\":
                    offset += 2
                    continue
                if char == quote:
                    quote = None
            elif char in {"'", '"'}:
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            offset += 1
        if depth:
            raise WorkatoFormulaError("unterminated message interpolation")
        parts.append(
            _Parser(text[start + 2 : offset - 1], reference_resolver).parse()
        )
        cursor = offset
    if not parts:
        return _literal("")
    if len(parts) == 1:
        return parts[0]
    return {"expression": {"op": "interpolate", "parts": parts}}


def _line_if_end(text: str, start: int) -> int:
    """Return the end offset of one balanced line-oriented ``=if`` block."""

    depth = 0
    cursor = start
    first = True
    while cursor < len(text):
        line_end = text.find("\n", cursor)
        if line_end < 0:
            line_end = len(text)
        raw_line = text[cursor:line_end]
        stripped = raw_line.strip()
        marker = stripped[1:].lstrip() if first and stripped.startswith("=") else stripped
        first = False
        if marker.startswith("if "):
            depth += 1
        elif re.match(r"^end(?:\b|:)", marker):
            depth -= 1
            if depth == 0:
                # ``end: value`` is an attachment-field delimiter.  Only the
                # ``end`` token belongs to the formula; its suffix is message
                # template text and must remain for the composite scanner.
                end_in_line = raw_line.find("end") + len("end")
                return cursor + end_in_line
        cursor = line_end + (line_end < len(text))
    raise WorkatoFormulaError("unterminated embedded if formula")


def _project_composite_formula(
    text: str, reference_resolver: ReferenceResolver
) -> dict[str, Any] | None:
    """Project Workato values flattened into a Slack message template.

    The Slack adapter deterministically joins independently configured block,
    message, and attachment-field values with newlines.  A resulting public
    ``text`` argument can therefore contain several complete ``=if ... end``
    formulas separated by ordinary message text.  It is not one Ruby program;
    parsing it as one would either fail or, worse, invent semantics.  This
    scanner restores exactly that join: evaluate each embedded formula, retain
    literal/interpolated message fragments, then concatenate them as text.
    """

    if not text.startswith("=if "):
        return None
    parts: list[dict[str, Any]] = []
    cursor = 0
    literal_start = 0

    def flush_literal(end: int) -> None:
        nonlocal literal_start
        if end > literal_start:
            parts.append(
                _project_template_text(
                    text[literal_start:end], reference_resolver
                )
            )

    while cursor < len(text):
        formula_start = cursor == 0 or text[cursor - 1] == "\n"
        if text.startswith("=if ", cursor) and formula_start:
            flush_literal(cursor)
            end = _line_if_end(text, cursor)
            projected = _project_if_formula(
                text[cursor + 1 : end], reference_resolver
            )
            if projected is None:
                raise WorkatoFormulaError("invalid embedded if formula")
            parts.append(projected)
            cursor = end
            literal_start = cursor
            continue
        # Scalar formulas occur after an attachment title delimiter, e.g.
        # ``Phone: =\"#{pill}\"``.  They occupy the remainder of that line.
        if text[cursor] == "=" and (
            formula_start or text[max(0, cursor - 2) : cursor] == ": "
        ):
            flush_literal(cursor)
            end = text.find("\n", cursor)
            if end < 0:
                end = len(text)
            parts.append(_Parser(text[cursor + 1 : end], reference_resolver).parse())
            cursor = end
            # Comment-only continuation lines are part of the Workato formula
            # value (not Slack-visible text).  Consume their leading newline,
            # but leave the newline that the Slack line join adds afterwards.
            while cursor < len(text) and text[cursor] == "\n":
                comment_end = text.find("\n", cursor + 1)
                if comment_end < 0:
                    comment_end = len(text)
                if not text[cursor + 1 : comment_end].lstrip().startswith("#"):
                    break
                cursor = comment_end
            literal_start = cursor
            continue
        cursor += 1
    flush_literal(len(text))
    if len(parts) <= 1:
        return None
    return {"expression": {"op": "interpolate", "parts": parts}}


def _project_hash_joined_reference_text(
    body: str, reference_resolver: ReferenceResolver
) -> dict[str, Any] | None:
    """Project Workato's formula-mode reference/literal concatenation idiom.

    Some exported menu-option values use ``#https://...`` as literal text
    between two bare ``_dp(...)`` calls.  In that adapter context ``#`` is a
    string separator, not a Ruby comment; the raw executor consequently
    interpolates every call into the surrounding text.  Treating it as a
    comment silently truncates the value after the first reference.
    """

    matches = list(_FORMULA_REFERENCE_RE.finditer(body))
    if len(matches) < 2 or not any(
        re.search(r"#(?!\{)", body[left.end() : right.start()])
        for left, right in zip(matches, matches[1:])
    ):
        return None
    if any(body[match.end() : match.end() + 1] in {".", "[", "&"} for match in matches):
        return None

    parts: list[dict[str, Any]] = []
    cursor = 0
    for match in matches:
        if match.start() > cursor:
            parts.append(_literal(body[cursor : match.start()]))
        payload = match.group("payload").replace("\\'", "'")
        if match.group("kind") == "_dp":
            try:
                decoded = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise WorkatoFormulaError(
                    "invalid _dp payload in hash-joined formula"
                ) from exc
            if not isinstance(decoded, dict):
                raise WorkatoFormulaError(
                    "non-object _dp payload in hash-joined formula"
                )
            parts.append(reference_resolver(decoded))
        else:
            if not payload.startswith("data."):
                raise WorkatoFormulaError(
                    f"unsupported Workato data reference {payload!r}"
                )
            path = payload[5:].split(".")
            if len(path) < 2:
                raise WorkatoFormulaError(
                    f"incomplete Workato data reference {payload!r}"
                )
            parts.append(
                reference_resolver(
                    {
                        "pill_type": (
                            "job_context"
                            if path[:2] == ["workato", "job_context"]
                            else "output"
                        ),
                        "provider": path[0],
                        "line": path[1],
                        "path": path[2:],
                    }
                )
            )
        cursor = match.end()
    if cursor < len(body):
        parts.append(_literal(body[cursor:]))
    return {"expression": {"op": "interpolate", "parts": parts}}


def project_workato_formula(
    value: str,
    reference_resolver: ReferenceResolver,
) -> dict[str, Any] | None:
    """Project one ``=`` formula or return ``None`` for an ordinary string.

    The parser is intentionally fail closed.  Callers must propagate
    :class:`WorkatoFormulaError`; falling back to ``{"literal": value}`` would
    silently recreate the binding-loss bug this module prevents.
    """

    if not isinstance(value, str) or not value.startswith("="):
        return None
    body = value[1:].strip()
    legacy_scalar_dispatch = "_dp(" in body
    if not body:
        return _literal("")
    conditional = _project_if_formula(body, reference_resolver)
    if conditional is not None:
        return conditional if legacy_scalar_dispatch else _typed_formula_results(conditional)
    composite = _project_composite_formula(value, reference_resolver)
    if composite is not None:
        return composite
    parsed = _Parser(body, reference_resolver).parse()
    return _runtime_formula_result(parsed) if legacy_scalar_dispatch else parsed


def workato_formula_references(value: str) -> list[dict[str, Any]]:
    """Return every lexical reference embedded in a Workato formula.

    Unlike :func:`project_workato_formula`, this helper does not need the
    surrounding expression to be supported.  The independent fidelity checker
    uses it to build the source-side binding multiset, so an unsupported
    operator cannot hide a datapill from the expected side of the comparison.
    """

    if not isinstance(value, str) or not value.startswith("="):
        return []
    # Prefer the real parser whenever the formula is in the supported
    # executable subset.  A lexical scan cannot reliably distinguish Ruby
    # string quotes from the JSON quotes inside ``#{_dp('...')}`` payloads;
    # in particular it used to treat the latter as closing the surrounding
    # string and then discard later interpolations as comments.  Collecting
    # references through the parser preserves every actually executed
    # interpolation.  Keep the scanner below as the fail-closed fallback for
    # unsupported syntax so it can still expose dependencies in diagnostics.
    parsed_references: list[dict[str, Any]] = []

    def collect(reference: dict[str, Any]) -> dict[str, Any]:
        parsed_references.append(reference)
        return {"literal": None}

    try:
        project_workato_formula(value, collect)
    except WorkatoFormulaError:
        pass
    else:
        return parsed_references

    # Match the runtime parser's Ruby comment behavior. A ``#`` outside a
    # quoted string discards the rest of that line, so datapills inside that
    # comment are not executable data dependencies.
    executable: list[str] = []
    quote: str | None = None
    escaped = False
    index = 0
    while index < len(value):
        char = value[index]
        if escaped:
            executable.append(char)
            escaped = False
        elif char == "\\" and quote:
            executable.append(char)
            escaped = True
        elif quote:
            executable.append(char)
            if char == quote:
                quote = None
        elif char in {"'", '"'}:
            executable.append(char)
            quote = char
        elif char == "#":
            while index < len(value) and value[index] != "\n":
                index += 1
            if index < len(value):
                executable.append("\n")
        else:
            executable.append(char)
        index += 1

    references: list[dict[str, Any]] = []
    for match in _FORMULA_REFERENCE_RE.finditer("".join(executable)):
        payload = match.group("payload").replace("\\'", "'")
        if match.group("kind") == "_dp":
            try:
                decoded = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict):
                references.append(decoded)
            continue
        if not payload.startswith("data."):
            continue
        parts = payload[5:].split(".")
        if len(parts) < 2:
            continue
        references.append(
            {
                "pill_type": (
                    "job_context"
                    if parts[:2] == ["workato", "job_context"]
                    else "output"
                ),
                "provider": parts[0],
                "line": parts[1],
                "path": parts[2:],
            }
        )
    return references
