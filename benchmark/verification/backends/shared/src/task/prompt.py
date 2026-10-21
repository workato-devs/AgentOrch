"""Builds the candidate-model prompt and asserts it leaks nothing from the
variant's expect block. Environment card exposes only what a real operator
would know: table ids/names/columns and the pinned clock — never row values."""

from __future__ import annotations

import json
from typing import Any

CONTROL_TOOLS_DOC = """
Control tools (always available, not part of the environment):
- {"tool": "finish", "args": {}} — declare the task complete.
- {"tool": "submit_answer", "args": {"answer": ...}} — return a final answer
  when the task asks for one, then stop.
- {"tool": "stop", "args": {"stop_reason": "...", "stop_with_error": true}}
  — execute an explicit workflow stop branch, preserving its reason and error flag.
"""

ACTION_GUIDANCE = """
Action budget: you have a limited number of tool calls. First infer the
intended business outcome from the goal, trigger event, environment cards,
and tool schemas. Use read-only tools only when they are necessary to
identify an existing record, resolve an ID, inspect current state, or avoid
an unsafe mutation. Prefer targeted reads over broad searches. Do not spend
actions verifying information already provided in the prompt or schema
cards. Once you have enough information to perform the required business
effect, execute the minimal set of actions in the dependency and control-flow
order implied by the requirements. Canonical tool choice and action order are
evaluated in addition to final state and terminal outputs.
"""

RESPONSE_RULES = """
Response format: reply with exactly ONE JSON object per turn:
{"thought": "...", "tool": "<tool name>", "args": { ... }}
No prose outside the JSON. Tool errors come back as observations — read them
and recover. Do not repeat identical calls.
"""


def expect_leak_values(expect: dict[str, Any]) -> set[str]:
    values: set[str] = set()

    def walk(node: Any, excluded: bool) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                # Tool-name lists are documented in the schemas; keys starting
                # with "_" are harness row metadata (_row_id, _created_by="seed")
                # and never task secrets. Neither is a leak.
                walk(value, key in ("tool", "tools", "trace_tools")
                     or str(key).startswith("_"))
        elif isinstance(node, list):
            for item in node:
                walk(item, excluded)
        elif isinstance(node, str) and not excluded and len(node) >= 4:
            values.add(node)

    walk(expect or {}, False)
    return values


def is_specific_value(value: str) -> bool:
    """Only SPECIFIC tokens count as leakable values (digit/uppercase/space,
    >= 6 chars): generic vocabulary like "true"/"Active" appears in ordinary
    prose and flagging it makes briefs unwritable. Shared by the offline gate
    (check_briefs) and the runtime gate (runner) so they can never diverge."""
    return len(value) >= 6 and (
        any(ch.isdigit() for ch in value)
        or any(ch.isupper() for ch in value)
        or any(ch.isspace() for ch in value)
    )


def value_restated(text: str, value: str) -> bool:
    """Case-sensitive word-boundary match: "isInactive" does not restate
    "Inactive"; prose "existing entries" does not restate "Existing"."""
    import re
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(value)}(?![A-Za-z0-9])",
                     text) is not None


def brief_leaks(text: str, expect: dict[str, Any]) -> list[str]:
    """Runtime leak gate over brief text with the SAME semantics as the
    offline check_briefs gate: specific values, case-sensitive word-boundary."""
    return sorted(v for v in expect_leak_values(expect)
                  if is_specific_value(v) and value_restated(text, v))


def check_prompt(text: str, expect: dict[str, Any]) -> list[str]:
    lowered = text.lower()
    return sorted(v for v in expect_leak_values(expect) if v.lower() in lowered)


def _column_keys(rows: list[Any]) -> list[str]:
    keys: set[str] = set()
    for row in rows:
        if isinstance(row, dict):
            keys.update(k for k in row if not str(k).startswith("_"))
    return sorted(keys)


def environment_card(seed: dict[str, Any]) -> str:
    lines: list[str] = ["ENVIRONMENT:"]
    if seed.get("now"):
        lines.append(f"- Current time (fixed): {seed['now']}")
    db = (seed.get("workato_db_table") or {}).get("tables") or {}
    for table_id, rows in sorted(db.items()):
        lines.append(f"- Data table {table_id}: columns {_column_keys(rows)}")
    lookup = seed.get("lookup_table") or {}
    names = {v: k for k, v in (lookup.get("names") or {}).items()}
    for table_id, rows in sorted((lookup.get("tables") or {}).items()):
        label = f" (name: {names[table_id]!r})" if table_id in names else ""
        lines.append(f"- Lookup table {table_id}{label}: columns {_column_keys(rows)}")
    if len(lines) == 1:
        lines.append("- No seeded tables.")
    return "\n".join(lines)


def output_contract_text(contract: dict[str, Any]) -> str:
    """Renders the MECHANICAL output contract (deterministically generated
    from the corpus, never LLM prose): only the response-envelope shape the
    task's terminal tools require. ``contract.constants`` is deliberately not
    rendered: legacy contracts aggregate values across hidden variants and can
    therefore contain evaluator answers rather than operator-visible input."""
    lines: list[str] = ["OUTPUT CONTRACT (interface documentation):"]
    if contract.get("schema_version") in {
        "public-output-interface",
        "public-output-schema-v1",
        "public-output-schema-v2",
    }:
        policy = str(contract.get("literal_precedence_policy") or "").strip()
        if policy:
            lines.append(f"- Literal type policy: {policy}")
        for item in contract.get("declared_responses") or []:
            status = item.get("http_status_code") or item.get("kind") or "response"
            delivery = str(item.get("delivery") or "").strip()
            delivery_text = f"; delivery: {delivery}" if delivery else ""
            lines.append(
                f"- Declared {status} body schema{delivery_text}: "
                + json.dumps(item.get("body_schema") or [], sort_keys=True)
            )
        for item in contract.get("terminal_contracts") or []:
            keys = item.get("argument_keys") or []
            label = item.get("tool") or item.get("kind") or "terminal output"
            lines.append(
                f"- {label} argument keys: " + json.dumps(keys, sort_keys=True)
            )
            literals = item.get("configured_literal_fields") or []
            if literals:
                lines.append(
                    f"- {label} configured literal fields: "
                    + json.dumps(literals, sort_keys=True)
                )
        return "\n".join(lines) if len(lines) > 1 else ""
    for item in contract.get("response_contracts") or []:
        lines.append(f"- {item['tool_family']} envelope keys: "
                     + json.dumps(item["keys"], sort_keys=True))
    return "\n".join(lines) if len(lines) > 1 else ""


def build_system_prompt(brief: dict[str, Any], tool_specs: list[dict[str, Any]],
                        mode_suffix: str, contract_text: str | None = None,
                        response_rules: str | None = None) -> str:
    for field in ("objective", "input_contract", "completion_criteria", "constraints"):
        if field not in brief:
            raise RuntimeError(f"task brief missing required field: {field}")
    specs = json.dumps(tool_specs, indent=1, sort_keys=True)
    parts = [
        "You are an automation agent. Complete the task using ONLY the tools below.",
        f"OBJECTIVE:\n{json.dumps(brief['objective'], indent=1)}",
        f"INPUT CONTRACT:\n{json.dumps(brief['input_contract'], indent=1)}",
        f"COMPLETION CRITERIA:\n{json.dumps(brief['completion_criteria'], indent=1)}",
        f"CONSTRAINTS:\n{json.dumps(brief['constraints'], indent=1)}",
    ]
    if contract_text:
        parts.append(contract_text)
    parts += [
        f"TOOLS:\n{specs}",
        CONTROL_TOOLS_DOC.strip(),
        ACTION_GUIDANCE.strip(),
        (response_rules or RESPONSE_RULES).strip(),
    ]
    if mode_suffix:
        parts.append(mode_suffix)
    return "\n\n".join(parts)


def runtime_input_parts(variant_input: dict[str, Any]) -> list[str]:
    """Render the public concrete runtime input exactly as ReAct sees it.

    This is the single representation of a variant's runtime input shown to
    a model before its first tool call: the trigger event and, when present,
    the public execution context. ReAct's first user turn and the
    GLOBAL+INPUT planner prompt both render through this function so the two
    settings receive byte-identical runtime-input text.
    """
    trigger = variant_input.get("trigger_input")
    if not isinstance(trigger, dict):
        raise RuntimeError("seed.variant_input.trigger_input missing")
    parts = [
        f"TRIGGER EVENT:\n{json.dumps(trigger, indent=1, sort_keys=True)}",
    ]
    execution_context = variant_input.get("execution_context")
    if isinstance(execution_context, dict) and execution_context:
        parts.append(
            "EXECUTION CONTEXT:\n"
            + json.dumps(execution_context, indent=1, sort_keys=True)
        )
    return parts


def build_first_user_turn(seed: dict[str, Any], schema_text: str | None = None) -> str:
    variant_input = seed.get("variant_input") or {}
    parts = runtime_input_parts(variant_input)
    parts.append(environment_card(seed))
    # Schema card is agent-visible-by-design (table column labels/types the
    # operator sees in the Workato UI) — appended after the environment card so
    # it shares the same leak-whitelist treatment as the rest of the first turn.
    if isinstance(schema_text, str) and schema_text.strip():
        parts.append(schema_text)
    parts.append("Begin. Emit your next action as JSON.")
    return "\n\n".join(parts)
