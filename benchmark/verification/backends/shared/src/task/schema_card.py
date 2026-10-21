"""Extracts agent-visible schema knowledge from the raw recipe: per-table
column schemas (uuid -> human label/type) and terminal-response contracts.
A real operator sees this in the Workato UI; without it, write targets are
opaque UUIDs and some tasks are logically unsolvable."""

from __future__ import annotations

import json
import re
from typing import Any

# Column labels of the form "$internal_value_<uuid>" are the recipe engine's
# placeholder for "no human label", not a real column name — treat as unlabeled.
_INTERNAL_LABEL = re.compile(r"^\$internal_value_")

# The same data-table column appears two ways across schema blocks: dash-escaped
# (the canonical UUID, carried by get_records INPUT schema with $internal_value
# placeholder labels) and underscore-escaped (carried by OUTPUT / update INPUT
# schemas with the real human labels). Normalizing UUID-shaped names to the dash
# form lets the human label from one block attach to the column keyed from the
# other. Non-UUID column ids (e.g. "id") pass through untouched.
_UUID_UNDERSCORE = re.compile(
    r"^[0-9a-fA-F]{8}_[0-9a-fA-F]{4}_[0-9a-fA-F]{4}_[0-9a-fA-F]{4}_[0-9a-fA-F]{12}$")
_UUID_DASH = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

_SCHEMA_KEYS = ("extended_input_schema", "extended_output_schema",
                "input_schema", "output_schema")

# Terminal actions whose input KEY structure is the response contract the agent
# must satisfy. Values are never surfaced (they embed pill/formula references).
_TERMINAL_ACTIONS = frozenset({
    ("workato_api_platform", "return_response"),       # api platform response
    ("workato_recipe_function", "return_result"),      # recipe function result
    ("workato_service", "send_reply"),                 # service reply
    ("workato_service", "call_service"),               # service call
    ("workato_service", "call_service_async"),
    ("workato_genie", "workflow_return_result"),       # genie return
    ("workato_pub_sub", "publish_to_topic"),           # pub/sub publish
    ("workato_pub_sub", "publish_to_topic_batch"),
})


def _canonical_column(name: str) -> str:
    """Dash-escaped UUID is the canonical column identity used to merge the
    labelled and placeholder forms of the same column."""
    if _UUID_UNDERSCORE.match(name):
        return name.replace("_", "-")
    return name


def _writable_column(name: str) -> str:
    """The data-table backend stores columns with dashes escaped to
    underscores, so the key an agent actually writes is the underscore form."""
    if _UUID_DASH.match(name):
        return name.replace("-", "_")
    return name


def _collect_fields(node: Any, out: dict[str, dict]) -> None:
    """Recursively harvest every schema field dict (one carrying both `name`
    and `label`) into out[canonical_name] = {"label": ..., "type": ...}.
    Real labels win over placeholder-derived None; a later real label wins."""
    if isinstance(node, dict):
        name = node.get("name")
        label = node.get("label")
        if isinstance(name, str) and isinstance(label, str):
            col = _canonical_column(name)
            real = None if _INTERNAL_LABEL.match(label) else label
            ftype = node.get("type") if isinstance(node.get("type"), str) else None
            existing = out.get(col)
            if existing is None:
                out[col] = {"label": real, "type": ftype}
            else:
                if real is not None:
                    existing["label"] = real
                if existing.get("type") is None and ftype is not None:
                    existing["type"] = ftype
        for value in node.values():
            _collect_fields(value, out)
    elif isinstance(node, list):
        for item in node:
            _collect_fields(item, out)


def table_schemas(raw: dict) -> dict[str, dict[str, dict]]:
    """table_id -> {column_name: {"label": <label or None>, "type": <type or None>}}.

    Every block whose `input` names a table_id/lookup_table_id contributes its
    schema-bearing lists; columns merge across all blocks touching the table."""
    result: dict[str, dict[str, dict]] = {}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            inp = node.get("input")
            if isinstance(inp, dict):
                table_id = inp.get("table_id") or inp.get("lookup_table_id")
                if table_id is not None:
                    cols = result.setdefault(str(table_id), {})
                    for key in _SCHEMA_KEYS:
                        if isinstance(node.get(key), list):
                            _collect_fields(node[key], cols)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(raw)
    return {tid: cols for tid, cols in result.items() if cols}


def _key_skeleton(node: Any) -> Any:
    """Structure of keys only — dict -> {key: skeleton}, list -> first
    element's skeleton, scalar -> None. Values are dropped so no formula or
    pill reference can leak."""
    if isinstance(node, dict):
        return {str(key): _key_skeleton(value) for key, value in node.items()}
    if isinstance(node, list):
        return _key_skeleton(node[0]) if node else None
    return None


def response_contracts(raw: dict) -> list[dict]:
    """For each terminal action, the key skeleton of its input (never values)."""
    contracts: list[dict] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("keyword") == "action" and (
                    node.get("provider"), node.get("name")) in _TERMINAL_ACTIONS:
                inp = node.get("input")
                if isinstance(inp, dict):
                    contracts.append({
                        "tool_family": f"{node['provider']}.{node['name']}",
                        "keys": _key_skeleton(inp),
                    })
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(raw)
    return contracts


def _seed_table_ids(seed: dict) -> set[str]:
    ids: set[str] = set()
    for section in ("workato_db_table", "lookup_table"):
        tables = (seed.get(section) or {}).get("tables") or {}
        ids.update(str(table_id) for table_id in tables)
    return ids


def _column_line(name: str, meta: dict) -> str:
    writable = _writable_column(name)
    label = meta.get("label")
    ftype = meta.get("type")
    if label and ftype:
        return f"  - {writable}: {label} ({ftype})"
    if label:
        return f"  - {writable}: {label}"
    if ftype:
        return f"  - {writable} ({ftype})"
    return f"  - {writable}"


def schema_card_text(raw: dict, seed: dict) -> str:
    """Human-readable schema section. Advertises table schemas only for tables
    the variant actually seeds, plus the recipe's terminal response contracts.
    Returns "" when there is nothing to add — never noise."""
    schemas = table_schemas(raw)
    seed_ids = _seed_table_ids(seed)

    lines: list[str] = []
    table_lines: list[str] = []
    for table_id in sorted(seed_ids):
        cols = schemas.get(table_id)
        if not cols:
            continue
        table_lines.append(f"- Data table {table_id} columns:")
        for name in sorted(cols):
            table_lines.append(_column_line(name, cols[name]))
    if table_lines:
        lines.append("TABLE SCHEMAS:")
        lines.extend(table_lines)

    contract_lines: list[str] = []
    seen: set[str] = set()
    for contract in response_contracts(raw):
        rendered = json.dumps(contract["keys"], sort_keys=True)
        dedup = f"{contract['tool_family']}:{rendered}"
        if dedup in seen:
            continue
        seen.add(dedup)
        contract_lines.append(f"- {contract['tool_family']} keys: {rendered}")
    if contract_lines:
        if lines:
            lines.append("")
        lines.append("RESPONSE CONTRACT:")
        lines.extend(contract_lines)

    return "\n".join(lines)
