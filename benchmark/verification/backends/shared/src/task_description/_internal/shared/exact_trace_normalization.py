"""Global representation-only normalization for exact trace comparison."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any


_QUERY_ARGUMENTS = {"query", "sql", "where", "orderby", "order_by"}
_QUERY_TOOLS = {
    "salesforce.search_records",
    "snowflake.run_custom_sql",
    "snowflake.search_rows",
    "snowflake.search_rows_sql",
    "snowflake.update_rows",
    "workato_db_table.search_records",
    "workato_smart_list.query_list",
}
_QUERY_KEYWORDS = {
    "ALL", "ALTER", "AND", "AS", "ASC", "BEGIN", "BETWEEN", "BY",
    "CASE", "CAST", "CREATE", "CROSS", "CURRENT_DATE", "CURRENT_TIMESTAMP",
    "DELETE", "DESC", "DESCRIBE", "DISTINCT", "DROP", "ELSE", "END",
    "EXISTS", "FALSE", "FROM", "FULL", "GROUP", "HAVING", "ILIKE", "IN",
    "INNER", "INSERT", "INTO", "IS", "JOIN", "LEFT", "LIKE", "LIMIT",
    "MERGE", "NOT", "NULL", "NULLS", "OFFSET", "ON", "OR", "ORDER",
    "OUTER", "QUALIFY", "RIGHT", "SELECT", "SET", "TABLE", "THEN", "TRUE",
    "UNION", "UPDATE", "USING", "VALUES", "WHEN", "WHERE", "WITH",
}


def _query_tokens(value: str) -> list[str]:
    """Tokenize SQL/SOQL without changing literals or structural choices."""

    tokens: list[str] = []
    index = 0
    length = len(value)
    while index < length:
        char = value[index]
        if char.isspace():
            index += 1
            continue
        if value.startswith("--", index):
            end = value.find("\n", index)
            end = length if end < 0 else end
            tokens.append(value[index:end])
            index = end
            continue
        if value.startswith("/*", index):
            end = value.find("*/", index + 2)
            end = length if end < 0 else end + 2
            tokens.append(value[index:end])
            index = end
            continue
        if char in {"'", '"', "`"}:
            quote = char
            start = index
            index += 1
            while index < length:
                if value[index] == quote:
                    if index + 1 < length and value[index + 1] == quote:
                        index += 2
                        continue
                    index += 1
                    break
                if value[index] == "\\" and index + 1 < length:
                    index += 2
                else:
                    index += 1
            tokens.append(value[start:index])
            continue
        operator = next(
            (
                candidate
                for candidate in ("<=>", "::", ">=", "<=", "!=", "<>", "=>", "||")
                if value.startswith(candidate, index)
            ),
            None,
        )
        if operator:
            tokens.append(operator)
            index += len(operator)
            continue
        word = re.match(r"[A-Za-z_][A-Za-z0-9_$]*", value[index:])
        if word:
            token = word.group(0)
            tokens.append(token.upper() if token.upper() in _QUERY_KEYWORDS else token)
            index += len(token)
            continue
        number = re.match(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value[index:])
        if number:
            token = number.group(0)
            tokens.append(token)
            index += len(token)
            continue
        tokens.append(char)
        index += 1
    if tokens and tokens[-1] == ";":
        tokens.pop()
    return tokens


def canonical_exact_argument_view(tool: str, arguments: Any) -> Any:
    """Return the globally scored representation of one call's arguments.

    This removes only documented transport/lexical representation choices.
    It never changes tool identity, scalar JSON types, list order, predicates,
    projections, field presence, or query token order.
    """

    value = deepcopy(arguments)
    if not isinstance(value, dict):
        return value
    if tool == "slack.post_reply":
        # Workato injects invoking-conversation transport fields before calling
        # the public connector.  The public action's canonical request leaves
        # those fields implicit; destination correctness remains enforced by
        # the resulting Slack side effect.
        for key in ("channel", "thread_ts", "user", "original_ts"):
            value.pop(key, None)
        for key in ("ephemeral", "replace_original", "delete_original"):
            if value.get(key) is False:
                value.pop(key)
    elif tool == "slack.post_message":
        # The simulator replaces configured destinations with an isolated
        # channel and fills blank thread/message transport fields. The public
        # side-effect gate separately proves the configured destination.
        for key in ("channel", "thread_ts", "ts"):
            value.pop(key, None)
    if tool in _QUERY_TOOLS:
        for key in _QUERY_ARGUMENTS & set(value):
            if isinstance(value[key], str):
                value[key] = {"__canonical_query_tokens__": _query_tokens(value[key])}
    return value


def exact_arguments_equal(tool: str, actual: Any, expected: Any) -> bool:
    """Compare arguments after the one public exact-trace normalization."""

    try:
        actual_json = json.dumps(
            canonical_exact_argument_view(tool, actual),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        expected_json = json.dumps(
            canonical_exact_argument_view(tool, expected),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError):
        return False
    return actual_json == expected_json
