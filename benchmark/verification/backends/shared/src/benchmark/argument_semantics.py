"""Conservative semantic comparison for benchmark tool arguments.

``args_contains`` historically meant literal recursive subset equality.  That
is useful as a canonical-trace diagnostic, but it is too strict for an
orchestration score: connector defaults, numeric JSON encodings, and equivalent
query surfaces can denote the same invocation.

This module keeps both signals.  ``raw_contains`` is the old comparator;
``compare_argument_subset`` first records that raw result and then applies only
small, connector-specific equivalences that can be established deterministically.
Unsupported query shapes fail closed.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from benchmark.lookup_table import canonical_lookup_parameters


_OPTIONAL_DEFAULTS: dict[str, dict[tuple[str, ...], Any]] = {
    "snowflake.run_custom_sql": {("parameters",): {}},
    "slack.post_message": {("thread_ts",): "", ("ts",): ""},
    "slack.post_reply": {("thread_ts",): ""},
    "workato_db_table.add_record": {("record_id_field",): None},
    "workato_db_table.update_record": {("record_id_field",): None},
    "workato_db_table.upsert_record": {("record_id_field",): None},
    "workato_service.send_reply": {("reply",): {}},
    "lookup_table.update_entry": {("ignore_not_found",): False},
    "lookup_table.delete_entry": {("ignore_not_found",): False},
}


def _default_equal(actual: Any, expected: Any) -> bool:
    if _scalar_equal(actual, expected):
        return True
    if isinstance(actual, bool) and isinstance(expected, str):
        return expected.strip().casefold() == str(actual).casefold()
    if isinstance(expected, bool) and isinstance(actual, str):
        return actual.strip().casefold() == str(expected).casefold()
    return False


def compare_argument_full(
    tool: str,
    actual: Any,
    expected: Any,
    *,
    evaluation_time: str | datetime | None = None,
    boolean_paths: set[tuple[str, ...]] | None = None,
) -> dict[str, Any]:
    """Compare a complete invocation after removing only benign encodings.

    Unlike ``compare_argument_subset``, this is symmetric: unrecognized extra
    arguments fail. Connector-declared empty defaults and a Slack ``blocks``
    projection that exactly duplicates ``text`` are representation choices,
    not different orchestration decisions.
    """

    raw_ok = actual == expected
    actual_view = _full_argument_view(tool, actual)
    expected_view = _full_argument_view(tool, expected)
    forward = compare_argument_subset(
        tool,
        actual_view,
        expected_view,
        evaluation_time=evaluation_time,
        boolean_paths=boolean_paths,
    )
    reverse = compare_argument_subset(
        tool,
        expected_view,
        actual_view,
        evaluation_time=evaluation_time,
        boolean_paths=boolean_paths,
    )
    semantic_ok = bool(forward["semantic_ok"] and reverse["semantic_ok"])
    return {
        "raw_ok": raw_ok,
        "semantic_ok": semantic_ok,
        "mode": (
            "raw_exact"
            if raw_ok
            else f"{forward['mode']}+{reverse['mode']}"
        ),
    }


def response_contains(
    tool: str,
    actual: Any,
    expected: Any,
    *,
    boolean_paths: set[tuple[str, ...]] | None = None,
) -> bool:
    """Compare a required response subset using public connector semantics."""

    if tool == "workato_api_platform.return_response":
        return _api_response_contains(
            actual,
            expected,
            boolean_paths=boolean_paths,
        )
    return _semantic_contains(
        tool,
        actual,
        expected,
        boolean_paths=boolean_paths,
    )


def compare_response_full(
    tool: str,
    actual: Any,
    expected: Any,
    *,
    boolean_paths: set[tuple[str, ...]] | None = None,
) -> bool:
    """Symmetric response comparison after connector-declared normalization."""

    return response_contains(
        tool,
        actual,
        expected,
        boolean_paths=boolean_paths,
    ) and response_contains(
        tool,
        expected,
        actual,
        boolean_paths=boolean_paths,
    )


def _full_argument_view(tool: str, value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    if tool == "slack_bot.open_bot_app_home":
        return canonical_slack_home_args(value)
    result = dict(value)
    for path, default in _OPTIONAL_DEFAULTS.get(tool, {}).items():
        if len(path) == 1 and path[0] in result and _default_equal(
            result[path[0]], default
        ):
            result.pop(path[0])
    if tool in {"slack.post_message", "slack.post_reply"}:
        blocks = result.get("blocks")
        text = result.get("text")
        if (
            isinstance(blocks, list)
            and len(blocks) == 1
            and isinstance(blocks[0], dict)
            and set(blocks[0]) == {"section_text"}
            and blocks[0]["section_text"] == text
        ):
            result.pop("blocks")
    return result


def canonical_slack_home_args(value: Any) -> Any:
    """Project private Workato and public Block Kit encodings to UI intent.

    App Home recipes are stored with Workato-only keys such as ``block_type``
    and ``bot_command``.  The public tool accepts a Slack view object, so
    orchestration and outcome scoring compare the user, visible ordered text,
    and visible controls rather than those private transport literals.
    """

    if not isinstance(value, dict):
        return value
    view = value.get("view")
    if not isinstance(view, dict):
        return value
    blocks = view.get("blocks")
    if not isinstance(blocks, list):
        return value
    texts: list[str] = []
    controls: list[dict[str, str]] = []
    images: list[dict[str, str]] = []
    fields: list[dict[str, str]] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        text = _slack_visible_text(block.get("text"))
        if not text:
            text = _slack_visible_text(block.get("section_text"))
        if text:
            texts.append(text)
        for field in block.get("attachment_fields") or block.get("fields") or []:
            if not isinstance(field, dict):
                continue
            field_intent = {
                "title": _slack_visible_text(field.get("title")),
                "value": _slack_visible_text(field.get("value") or field.get("text")),
            }
            if field_intent["title"] or field_intent["value"]:
                fields.append(field_intent)
        if block.get("image_url") not in (None, ""):
            images.append({
                "url": str(block.get("image_url")),
                "alt": _slack_visible_text(
                    block.get("alt_text") or block.get("image_title")
                ),
            })
        direct = _slack_button_intent(block)
        if direct:
            controls.append(direct)
        candidates: list[Any] = []
        if isinstance(block.get("accessory"), dict):
            candidates.append(block["accessory"])
        candidates.extend(block.get("actions") or [])
        candidates.extend(block.get("elements") or [])
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            button = _slack_button_intent(candidate)
            if button:
                controls.append(button)
            elif _slack_visible_text(candidate.get("text")):
                texts.append(_slack_visible_text(candidate.get("text")))
    intent: dict[str, Any] = {
        "texts": texts,
        "controls": controls,
    }
    if images:
        intent["images"] = images
    if fields:
        intent["fields"] = fields
    return {
        "user_id": value.get("user_id"),
        "view_intent": intent,
    }


def _slack_visible_text(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("text") or "")
    return str(value or "")


def _slack_button_intent(value: dict[str, Any]) -> dict[str, str] | None:
    title = value.get("button_title")
    if title in (None, ""):
        value_type = str(value.get("type") or value.get("element_type") or "")
        if value_type != "button":
            return None
        title = _slack_visible_text(value.get("text") or value.get("button_text"))
    if title in (None, ""):
        return None
    result = {"label": str(title)}
    style = str(value.get("style") or "")
    if style:
        result["style"] = style
    if value.get("url") not in (None, ""):
        result["url"] = str(value["url"])
    return result


def raw_contains(actual: Any, expected: Any) -> bool:
    """Original ``args_contains`` behavior, retained as a diagnostic."""

    if expected == "__ANY__":
        return actual not in (None, "")
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        return all(
            key in actual and raw_contains(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return False
        return all(
            raw_contains(actual[idx], value)
            for idx, value in enumerate(expected)
        )
    # Python considers ``True == 1`` and ``1 == 1.0``. Canonical JSON does
    # not: scalar representation is part of the authoritative call arguments.
    return type(actual) is type(expected) and actual == expected


def compare_argument_subset(
    tool: str,
    actual: Any,
    expected: Any,
    *,
    evaluation_time: str | datetime | None = None,
    boolean_paths: set[tuple[str, ...]] | None = None,
) -> dict[str, Any]:
    """Return raw and semantic subset results plus the accepted mode.

    The semantic comparator is deliberately asymmetric because the fixture
    names a required subset while an agent may supply benign extra arguments.
    """

    raw_ok = raw_contains(actual, expected)
    if raw_ok:
        return {"raw_ok": True, "semantic_ok": True, "mode": "raw_subset"}
    if not isinstance(actual, dict) or not isinstance(expected, dict):
        semantic_ok = _semantic_contains(
            tool, actual, expected, boolean_paths=boolean_paths
        )
        return {
            "raw_ok": False,
            "semantic_ok": semantic_ok,
            "mode": "typed_subset" if semantic_ok else "mismatch",
        }
    if tool in {"slack.post_message", "slack.post_reply"}:
        actual_view = dict(actual)
        expected_view = dict(expected)
        # The isolated simulator routes public channels through its physical
        # sink.  That connector-side routing is not a different orchestration
        # choice; DM targets remain untouched and therefore stay strict.
        if (
            actual_view.get("channel") == "C_SIMULATED"
            and str(expected_view.get("channel") or "")
            and not str(expected_view.get("channel") or "").startswith("U")
        ):
            actual_view["channel"] = expected_view["channel"]
        semantic_ok = _semantic_contains(
            tool,
            actual_view,
            expected_view,
            boolean_paths=boolean_paths,
        )
        return {
            "raw_ok": False,
            "semantic_ok": semantic_ok,
            "mode": "slack_routing_semantics" if semantic_ok else "mismatch",
        }
    if tool == "clock.wait_for_interval":
        actual_seconds = _duration_seconds(actual.get("interval"))
        expected_seconds = _duration_seconds(expected.get("interval"))
        semantic_ok = (
            actual_seconds is not None
            and expected_seconds is not None
            and actual_seconds == expected_seconds
        )
        return {
            "raw_ok": False,
            "semantic_ok": semantic_ok,
            "mode": "duration_semantics" if semantic_ok else "mismatch",
        }
    if tool == "salesforce.search_records":
        semantic_ok = _salesforce_search_contains(
            actual,
            expected,
            evaluation_time=evaluation_time,
        )
        return {
            "raw_ok": False,
            "semantic_ok": semantic_ok,
            "mode": "salesforce_query_semantics" if semantic_ok else "mismatch",
        }
    if tool == "snowflake.run_custom_sql" and "sql" in expected:
        semantic_ok = _snowflake_sql_contains(actual, expected)
        return {
            "raw_ok": False,
            "semantic_ok": semantic_ok,
            "mode": "snowflake_sql_semantics" if semantic_ok else "mismatch",
        }
    if tool == "snowflake.upsert_rows_batch":
        semantic_ok = _semantic_contains(
            tool,
            _canonical_snowflake_upsert_args(actual),
            _canonical_snowflake_upsert_args(expected),
            boolean_paths=boolean_paths,
        )
        return {
            "raw_ok": False,
            "semantic_ok": semantic_ok,
            "mode": "snowflake_upsert_semantics" if semantic_ok else "mismatch",
        }
    if tool == "workato_db_table.get_records" and "filters" in expected:
        semantic_ok = _workato_db_get_records_contains(actual, expected)
        return {
            "raw_ok": False,
            "semantic_ok": semantic_ok,
            "mode": "workato_db_filter_semantics" if semantic_ok else "mismatch",
        }
    if tool == "workato_api_platform.return_response":
        semantic_ok = _api_response_contains(
            actual, expected, boolean_paths=boolean_paths
        )
        return {
            "raw_ok": False,
            "semantic_ok": semantic_ok,
            "mode": "api_response_semantics" if semantic_ok else "mismatch",
        }
    if tool == "slack_bot.open_bot_app_home":
        actual_intent = canonical_slack_home_args(actual)
        expected_intent = canonical_slack_home_args(expected)
        semantic_ok = _semantic_contains(
            tool,
            actual_intent,
            expected_intent,
            boolean_paths=boolean_paths,
        )
        return {
            "raw_ok": False,
            "semantic_ok": semantic_ok,
            "mode": "slack_home_semantics" if semantic_ok else "mismatch",
        }
    if tool.startswith("lookup_table."):
        actual_view = _canonical_lookup_args(actual)
        expected_view = _canonical_lookup_args(expected)
        semantic_ok = _semantic_contains(
            tool,
            actual_view,
            expected_view,
            boolean_paths=boolean_paths,
        )
        return {
            "raw_ok": False,
            "semantic_ok": semantic_ok,
            "mode": "lookup_table_column_semantics" if semantic_ok else "mismatch",
        }
    semantic_ok = _semantic_contains(
        tool, actual, expected, boolean_paths=boolean_paths
    )
    return {
        "raw_ok": False,
        "semantic_ok": semantic_ok,
        "mode": "typed_defaults" if semantic_ok else "mismatch",
    }


def _canonical_snowflake_upsert_args(value: Any) -> Any:
    """Normalize public values and Workato Snowflake transport encodings."""

    def scalar(item: Any) -> Any:
        if isinstance(item, dict):
            out: dict[str, Any] = {}
            for key, child in item.items():
                normalized_key = str(key).casefold()
                normalized_child = scalar(child)
                if normalized_key in out and out[normalized_key] != normalized_child:
                    out[f"{normalized_key}#case_conflict"] = normalized_child
                else:
                    out[normalized_key] = normalized_child
            return out
        if isinstance(item, list):
            return [scalar(child) for child in item]
        if isinstance(item, str) and len(item) >= 2:
            if item.startswith("'") and item.endswith("'"):
                return item[1:-1].replace("''", "'")
        return item

    if not isinstance(value, dict):
        return scalar(value)
    result = scalar(value)
    raw_keys = result.get("key_columns")
    if isinstance(raw_keys, list):
        keys = raw_keys
    else:
        keys = re.split(r"[\n,]", str(raw_keys or ""))
    result["key_columns"] = sorted(
        str(key).strip().casefold() for key in keys if str(key).strip()
    )
    if "table" in result:
        result["table"] = str(result["table"]).casefold()
    return result


def _canonical_lookup_args(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    result = dict(value)
    if "ignore_not_found" in result:
        raw_ignore = result["ignore_not_found"]
        if isinstance(raw_ignore, str) and raw_ignore.strip().casefold() in {
            "true",
            "false",
        }:
            result["ignore_not_found"] = raw_ignore.strip().casefold() == "true"
    table_id = result.get("lookup_table_id", result.get("table_id"))
    if isinstance(result.get("parameters"), dict):
        result["parameters"] = canonical_lookup_parameters(
            table_id,
            result["parameters"],
        )
    if isinstance(result.get("entries"), list):
        result["entries"] = [
            canonical_lookup_parameters(table_id, item)
            if isinstance(item, dict)
            else item
            for item in result["entries"]
        ]
    return result


def _semantic_contains(
    tool: str,
    actual: Any,
    expected: Any,
    path: tuple[str, ...] = (),
    *,
    boolean_paths: set[tuple[str, ...]] | None = None,
) -> bool:
    if expected == "__ANY__":
        return actual not in (None, "")
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        defaults = _OPTIONAL_DEFAULTS.get(tool, {})
        for key, value in expected.items():
            child_path = path + (str(key),)
            if key not in actual:
                if child_path in defaults and _default_equal(
                    defaults[child_path], value
                ):
                    continue
                return False
            if not _semantic_contains(
                tool,
                actual[key],
                value,
                child_path,
                boolean_paths=boolean_paths,
            ):
                return False
        return True
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return False
        return all(
            _semantic_contains(
                tool,
                actual[idx],
                value,
                path + (str(idx),),
                boolean_paths=boolean_paths,
            )
            for idx, value in enumerate(expected)
        )
    if _path_matches(path, boolean_paths) and _boolean_equal(actual, expected):
        return True
    return _scalar_equal(actual, expected)


def _workato_db_get_records_contains(
    actual: dict[str, Any], expected: dict[str, Any]
) -> bool:
    for key, value in expected.items():
        if key == "filters":
            continue
        if key not in actual or not _semantic_contains(
            "workato_db_table.get_records", actual[key], value, (str(key),)
        ):
            return False
    actual_filters = actual.get("filters") or []
    expected_filters = expected.get("filters") or []
    if not isinstance(actual_filters, list) or not isinstance(expected_filters, list):
        return False
    if len(actual_filters) != len(expected_filters):
        return False

    def canonical(value: Any) -> tuple[str, str, Any] | None:
        if not isinstance(value, dict):
            return None
        field = str(value.get("field_id") or "")
        if field in {
            "record_id",
            "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
        }:
            field = "record_id"
        op = str(value.get("op", value.get("op_default", "eq"))).casefold()
        if op == "equals":
            op = "eq"
        operand = value.get("value", value.get("value_default"))
        if op in {"isnull", "isnotnull"}:
            # Workato retains a stale value_default for presence operators;
            # the adapter intentionally ignores it.
            operand = None
        elif isinstance(operand, str) and operand.strip().casefold() in {
            "true",
            "false",
        }:
            operand = operand.strip().casefold() == "true"
        elif isinstance(operand, (int, float, Decimal)) and not isinstance(
            operand, bool
        ):
            operand = Decimal(str(operand))
        elif isinstance(operand, str):
            try:
                operand = Decimal(operand.strip())
            except InvalidOperation:
                pass
        return (field, op, operand)

    actual_values = [canonical(item) for item in actual_filters]
    expected_values = [canonical(item) for item in expected_filters]
    return None not in actual_values and sorted(
        actual_values, key=lambda item: repr(item)
    ) == sorted(expected_values, key=lambda item: repr(item))


def _duration_seconds(value: Any) -> Decimal | None:
    text = str(value or "").strip().casefold()
    try:
        return Decimal(text)
    except InvalidOperation:
        pass
    match = re.fullmatch(
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*"
        r"(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h)",
        text,
    )
    if not match:
        return None
    amount, unit = match.groups()
    multiplier = (
        Decimal(1)
        if unit.startswith(("s", "sec"))
        else Decimal(60)
        if unit.startswith(("m", "min"))
        else Decimal(3600)
    )
    return Decimal(amount) * multiplier


def _api_response_contains(
    actual: dict[str, Any],
    expected: dict[str, Any],
    *,
    boolean_paths: set[tuple[str, ...]] | None = None,
) -> bool:
    if not isinstance(actual, dict) or not isinstance(expected, dict):
        return False

    def normalize_error_text(value: Any, key: str = "") -> Any:
        if isinstance(value, dict):
            return {
                str(child_key): normalize_error_text(child, str(child_key))
                for child_key, child in value.items()
            }
        if isinstance(value, list):
            return [normalize_error_text(child, key) for child in value]
        if key in {"message", "error"} and isinstance(value, str):
            return re.sub(r"^\s*ERROR:\s*", "", value, count=1, flags=re.I)
        return value

    actual_view = normalize_error_text(dict(actual))
    expected_view = normalize_error_text(dict(expected))
    actual_status = str(actual_view.get("http_status_code") or "")
    expected_status = str(expected_view.get("http_status_code") or "")
    if actual_status == expected_status == "204":
        if actual_view.get("response") in (None, {}):
            actual_view.pop("response", None)
        if expected_view.get("response") in (None, {}):
            expected_view.pop("response", None)
    return _semantic_contains(
        "workato_api_platform.return_response",
        actual_view,
        expected_view,
        boolean_paths=boolean_paths,
    )


def _path_matches(
    path: tuple[str, ...], patterns: set[tuple[str, ...]] | None
) -> bool:
    return bool(
        patterns
        and any(
            len(pattern) == len(path)
            and all(expected == "*" or expected == actual for expected, actual in zip(pattern, path))
            for pattern in patterns
        )
    )


def _boolean_equal(actual: Any, expected: Any) -> bool:
    def parse(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().casefold()
            if lowered == "true":
                return True
            if lowered == "false":
                return False
        return None

    actual_bool = parse(actual)
    expected_bool = parse(expected)
    return (
        actual_bool is not None
        and expected_bool is not None
        and actual_bool is expected_bool
    )


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None
    if isinstance(value, str) and re.fullmatch(
        r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", value.strip()
    ):
        try:
            return Decimal(value.strip())
        except InvalidOperation:
            return None
    return None


def _scalar_equal(actual: Any, expected: Any) -> bool:
    if actual == expected:
        return True
    actual_number = _decimal(actual)
    expected_number = _decimal(expected)
    return (
        actual_number is not None
        and expected_number is not None
        and actual_number == expected_number
    )


_SF_RESERVED_KEYS = {"query", "filters", "limit", "sobject"}
_SF_SELECT_RE = re.compile(
    r"^\s*select\s+.+?\s+from\s+([\w.]+)(.*)$",
    flags=re.IGNORECASE | re.DOTALL,
)


def _salesforce_search_contains(
    actual: dict[str, Any],
    expected: dict[str, Any],
    *,
    evaluation_time: str | datetime | None,
) -> bool:
    for key, value in expected.items():
        if key in _SF_RESERVED_KEYS:
            continue
        if key not in actual or not _semantic_contains(
            "salesforce.search_records", actual[key], value, (str(key),)
        ):
            return False

    expected_query = _parse_salesforce_query(expected.get("query", ""))
    actual_query = _parse_salesforce_query(actual.get("query", ""))
    expected_sobject = str(expected.get("sobject") or expected_query["sobject"])
    actual_sobject = str(actual.get("sobject") or actual_query["sobject"])
    if "sobject" in expected and expected_sobject.casefold() != actual_sobject.casefold():
        return False
    if expected_query["sobject"] and (
        expected_query["sobject"].casefold() != actual_sobject.casefold()
    ):
        return False
    if actual_query["sobject"] and actual_sobject and (
        actual_query["sobject"].casefold() != actual_sobject.casefold()
    ):
        return False

    expected_conditions = set(expected_query["conditions"])
    actual_conditions = set(actual_query["conditions"])
    if "filters" in expected:
        expected_conditions.update(_salesforce_filter_conditions(expected["filters"]))
    if "filters" in actual:
        actual_conditions.update(_salesforce_filter_conditions(actual["filters"]))
    if "query" in expected or "filters" in expected:
        # Query/filter representation may change; the selection predicate may
        # not. Extra predicates are material because they can hide rows.
        if not _salesforce_conditions_equal(
            expected_conditions,
            actual_conditions,
            evaluation_time=evaluation_time,
        ):
            return False

    expected_order = expected_query["order"]
    actual_order = actual_query["order"]
    if expected_order and expected_order != actual_order:
        return False

    if "limit" in expected:
        actual_limit = actual.get("limit", actual_query["limit"])
        if not _scalar_equal(actual_limit, expected["limit"]):
            return False
    elif expected_query["limit"] is not None:
        actual_limit = actual.get("limit", actual_query["limit"])
        if not _scalar_equal(actual_limit, expected_query["limit"]):
            return False
    return True


def _salesforce_conditions_equal(
    expected: set[str],
    actual: set[str],
    *,
    evaluation_time: str | datetime | None,
) -> bool:
    if expected == actual:
        return True
    reference = _parse_reference_time(evaluation_time)
    if reference is None:
        return False
    missing = set(expected - actual)
    extra = set(actual - expected)
    for expected_condition in list(missing):
        relative = re.fullmatch(
            r"([\w.]+) = last_n_days:(\d+)",
            expected_condition,
            flags=re.IGNORECASE,
        )
        if not relative:
            continue
        field, days_text = relative.groups()
        cutoff_date = (reference - timedelta(days=int(days_text))).date()
        match = next(
            (
                actual_condition
                for actual_condition in extra
                if _absolute_cutoff_matches(
                    actual_condition,
                    field.casefold(),
                    cutoff_date,
                )
            ),
            None,
        )
        if match is not None:
            missing.remove(expected_condition)
            extra.remove(match)
    return not missing and not extra


def _parse_reference_time(value: str | datetime | None) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(
                value.strip().replace("Z", "+00:00")
            )
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _absolute_cutoff_matches(
    condition: str,
    field: str,
    cutoff_date: Any,
) -> bool:
    match = re.fullmatch(
        rf"{re.escape(field)} >= (.+)",
        condition,
        flags=re.IGNORECASE,
    )
    if not match:
        return False
    value = match.group(1).strip().strip("'\"")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.date() == cutoff_date


def _parse_salesforce_query(value: Any) -> dict[str, Any]:
    query = str(value or "").strip().rstrip(";").strip()
    sobject = ""
    body = query
    select_match = _SF_SELECT_RE.match(query)
    if select_match:
        sobject = select_match.group(1)
        body = select_match.group(2).strip()
        if body.lower().startswith("where "):
            body = body[6:].strip()

    limit = None
    limit_match = re.search(r"\blimit\s+(\d+)\s*$", body, flags=re.IGNORECASE)
    if limit_match:
        limit = int(limit_match.group(1))
        body = body[: limit_match.start()].strip()

    order: tuple[tuple[str, str], ...] = ()
    order_match = re.search(r"\border\s+by\s+(.+)$", body, flags=re.IGNORECASE)
    if order_match:
        order_items: list[tuple[str, str]] = []
        for item in order_match.group(1).split(","):
            parts = item.strip().split()
            if not parts:
                continue
            direction = parts[1].casefold() if len(parts) > 1 else "asc"
            order_items.append((parts[0].casefold(), direction))
        order = tuple(order_items)
        body = body[: order_match.start()].strip()

    if body.lower().startswith("where "):
        body = body[6:].strip()
    conditions = tuple(
        sorted(
            _normalize_salesforce_condition(part)
            for part in re.split(r"\s+and\s+", body, flags=re.IGNORECASE)
            if part.strip()
        )
    )
    return {
        "sobject": sobject,
        "conditions": conditions,
        "order": order,
        "limit": limit,
    }


def _salesforce_filter_conditions(filters: Any) -> tuple[str, ...]:
    if not isinstance(filters, list):
        return ("<invalid-filters>",)
    conditions: list[str] = []
    operators = {
        "eq": "=",
        "equals": "=",
        "ne": "!=",
        "not_equal": "!=",
        "gt": ">",
        "gte": ">=",
        "lt": "<",
        "lte": "<=",
    }
    for item in filters:
        if not isinstance(item, dict) or not item.get("field"):
            return ("<invalid-filters>",)
        operator = operators.get(str(item.get("op") or "eq").casefold())
        if operator is None:
            return ("<invalid-filters>",)
        conditions.append(
            _normalize_salesforce_condition(
                f"{item['field']} {operator} {_salesforce_literal(item.get('value'))}"
            )
        )
    return tuple(sorted(conditions))


def _salesforce_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _normalize_salesforce_condition(condition: str) -> str:
    value = condition.strip()
    while value.startswith("(") and value.endswith(")"):
        value = value[1:-1].strip()
    value = re.sub(r"\s+", " ", value)
    disjuncts = re.split(r"\s+or\s+", value, flags=re.IGNORECASE)
    if len(disjuncts) > 1:
        # OR is commutative for these atomic connector predicates. Normalize
        # each comparison independently so `<>` and `!=` are equivalent even
        # when both occur inside the same parenthesized disjunction.
        return " or ".join(
            sorted(_normalize_salesforce_condition(item) for item in disjuncts)
        )
    match = re.fullmatch(
        r"([\w.]+)\s*(=|!=|<>|>=|<=|>|<)\s*(.+)",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return value.casefold()
    field, operator, raw_value = match.groups()
    normalized_value = raw_value.strip()
    if (
        len(normalized_value) >= 2
        and normalized_value[0] == normalized_value[-1]
        and normalized_value[0] in {"'", '"'}
    ):
        normalized_value = normalized_value[1:-1]
    if normalized_value.casefold() in {"true", "false"}:
        normalized_value = normalized_value.casefold()
    elif re.fullmatch(r"last_n_days:\d+", normalized_value, re.IGNORECASE):
        normalized_value = normalized_value.casefold()
    return f"{field.casefold()} {operator.replace('<>', '!=')} {normalized_value}"


def _snowflake_sql_contains(
    actual: dict[str, Any], expected: dict[str, Any]
) -> bool:
    actual_other = {key: value for key, value in actual.items() if key != "sql"}
    expected_other = {
        key: value for key, value in expected.items() if key != "sql"
    }
    if not _semantic_contains(
        "snowflake.run_custom_sql", actual_other, expected_other
    ):
        return False
    if "sql" not in actual:
        return False
    return _sql_semantically_equal(str(actual["sql"]), str(expected["sql"]))


def _sql_semantically_equal(actual: str, expected: str) -> bool:
    if _canonical_sql_text(actual) == _canonical_sql_text(expected):
        return True
    actual_anti = _parse_ctas_antijoin(actual)
    expected_anti = _parse_ctas_antijoin(expected)
    return actual_anti is not None and actual_anti == expected_anti


def _canonical_sql_text(sql: str) -> str:
    value = re.sub(r"\s+", " ", sql.strip().rstrip(";").strip())
    value = re.sub(r"\s*,\s*", ",", value)
    value = re.sub(r"\s*=\s*", "=", value)
    return _casefold_sql_outside_quotes(value)


def _casefold_sql_outside_quotes(value: str) -> str:
    out: list[str] = []
    quote: str | None = None
    idx = 0
    while idx < len(value):
        char = value[idx]
        if quote is not None:
            out.append(char)
            if char == quote:
                if idx + 1 < len(value) and value[idx + 1] == quote:
                    idx += 1
                    out.append(value[idx])
                else:
                    quote = None
        elif char in {"'", '"'}:
            quote = char
            out.append(char)
        else:
            out.append(char.casefold())
        idx += 1
    return "".join(out)


def _parse_ctas_antijoin(sql: str) -> dict[str, Any] | None:
    """Parse a conservative CTAS anti-join subset.

    Accepted exclusion encodings are ``LEFT JOIN ... WHERE right.key IS NULL``
    and a correlated ``NOT EXISTS``. Any additional unsupported join or nested
    predicate makes parsing fail instead of guessing equivalence.
    """

    value = re.sub(r"\s+", " ", sql.strip().rstrip(";").strip())
    if "'" in value or '"' in value:
        return None
    value = value.casefold()
    match = re.fullmatch(
        r"create\s+or\s+replace\s+table\s+([\w.$\"]+)\s+as\s+"
        r"select\s+(.+?)\s+from\s+([\w.$\"]+)\s+(?:as\s+)?(\w+)\s+(.+)",
        value,
    )
    if not match:
        return None
    target, projection_text, source, source_alias, tail = match.groups()
    projection = tuple(
        _normalize_projection(item.strip(), source_alias)
        for item in projection_text.split(",")
    )

    exclusion: tuple[str, str, str] | None = None
    where_text = ""
    left_join = re.fullmatch(
        r"left\s+join\s+([\w.$\"]+)\s+(?:as\s+)?(\w+)\s+on\s+"
        r"(.+?)\s+where\s+(.+)",
        tail,
    )
    if left_join:
        excluded_table, excluded_alias, on_text, where_text = left_join.groups()
        relation = _equality_sides(on_text)
        if relation is None:
            return None
        left, right = relation
        source_side = next(
            (side for side in (left, right) if side.startswith(source_alias + ".")),
            None,
        )
        excluded_side = next(
            (side for side in (left, right) if side.startswith(excluded_alias + ".")),
            None,
        )
        if source_side is None or excluded_side is None:
            return None
        null_pattern = re.compile(
            rf"(?:^|\s+and\s+){re.escape(excluded_side)}\s+is\s+null(?:$|\s+and\s+)",
        )
        if not null_pattern.search(where_text):
            return None
        where_text = null_pattern.sub(" and ", where_text).strip(" ")
        exclusion = (
            _strip_alias(source_side, source_alias),
            excluded_table,
            _strip_alias(excluded_side, excluded_alias),
        )
    else:
        if not tail.startswith("where "):
            return None
        where_text = tail[6:].strip()
        not_exists = re.search(
            r"not\s+exists\s*\(\s*select\s+1\s+from\s+"
            r"([\w.$\"]+)\s+(?:as\s+)?(\w+)\s+where\s+(.+?)\s*\)",
            where_text,
        )
        if not not_exists:
            return None
        excluded_table, excluded_alias, relation_text = not_exists.groups()
        relation = _equality_sides(relation_text)
        if relation is None:
            return None
        left, right = relation
        source_side = next(
            (side for side in (left, right) if side.startswith(source_alias + ".")),
            None,
        )
        excluded_side = next(
            (side for side in (left, right) if side.startswith(excluded_alias + ".")),
            None,
        )
        if source_side is None or excluded_side is None:
            return None
        exclusion = (
            _strip_alias(source_side, source_alias),
            excluded_table,
            _strip_alias(excluded_side, excluded_alias),
        )
        where_text = (
            where_text[: not_exists.start()] + where_text[not_exists.end() :]
        ).strip()

    where_text = re.sub(
        r"(?:^\s*and\s+|\s+and\s*$)",
        "",
        where_text,
    ).strip()
    predicates = []
    for predicate in re.split(r"\s+and\s+", where_text):
        normalized = predicate.strip().strip("() ")
        if not normalized or normalized == "1=1":
            continue
        normalized = _strip_alias(normalized, source_alias)
        normalized = re.sub(r"\s*=\s*true$", "", normalized).strip()
        if not re.fullmatch(r"[\w.$\"]+", normalized):
            return None
        predicates.append(normalized)
    if exclusion is None:
        return None
    return {
        "target": target,
        "projection": projection,
        "source": source,
        "predicates": tuple(sorted(predicates)),
        "exclusion": exclusion,
    }


def _equality_sides(value: str) -> tuple[str, str] | None:
    match = re.fullmatch(r"\s*([\w.$\"]+)\s*=\s*([\w.$\"]+)\s*", value)
    return (match.group(1), match.group(2)) if match else None


def _strip_alias(value: str, alias: str) -> str:
    return re.sub(rf"\b{re.escape(alias)}\.", "", value).strip()


def _normalize_projection(value: str, source_alias: str) -> str:
    """Remove a source qualifier and a provably redundant output alias."""

    normalized = _strip_alias(value, source_alias)
    match = re.fullmatch(r"([\w.$\"]+)\s+as\s+([\w$\"]+)", normalized)
    if match and match.group(1).rsplit(".", 1)[-1] == match.group(2):
        return match.group(1)
    return normalized
