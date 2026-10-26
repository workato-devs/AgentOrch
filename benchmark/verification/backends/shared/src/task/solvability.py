"""Classifies every ground-truth-required value of a task as input-derivable
(present in the trigger/seed the agent sees) or a recipe CONSTANT (a fixed
business rule). Constants must be stated in the task brief — an operator
cannot guess them; input-derivable values must NOT be, or the brief shortcuts
the derivation work the benchmark measures."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Tool-name suffixes that mark a pure READ expectation. The values inside a
# read expectation's args_contains are query parameters the agent supplies (a
# filter, an id), not ground-truth outputs the benchmark requires — so they are
# not "required values". Everything else (writes + terminal outputs) is.
READ_SUFFIXES = ("get_records", "search_records", "get_entries",
                 "get_entry", "search_entries")

# Keys that carry terminal-output expectations regardless of the tool.
OUTPUT_KEYS = ("response_contains", "result_contains")

# Registered tool-name prefixes. A brief that names a tool is workflow leakage:
# it tells the operator HOW rather than WHAT. Kept static (no import of the live
# registry) so the brief checker has no runtime backend dependency.
TOOL_PREFIXES = (
    "workato_db_table.", "lookup_table.", "workato_api_platform.",
    "workato_recipe_function.", "workato_service.", "workato_genie.",
    "workato_pub_sub.", "workato_variable.", "workato_app.",
    "slack.", "google_sheets.", "jira.", "salesforce.", "snowflake.",
)

_TOOL_TOKEN_RE = re.compile(r"[a-z0-9_]+\.[a-z0-9_]+")


def _collect_strings(node: Any, values: set[str], excluded: bool) -> None:
    """Walk ``node`` collecting string scalars (len >= 4) that are neither
    harness row metadata (keys starting with ``_``) nor tool-name lists. Mirrors
    the walking style of task.prompt.expect_leak_values."""
    if isinstance(node, dict):
        for key, value in node.items():
            _collect_strings(value, values,
                             key in ("tool", "tools", "trace_tools")
                             or str(key).startswith("_"))
    elif isinstance(node, list):
        for item in node:
            _collect_strings(item, values, excluded)
    elif isinstance(node, str) and not excluded and len(node) >= 4:
        values.add(node)


def required_values(expect: dict) -> set[str]:
    """Ground-truth values the benchmark requires: string scalars drawn from
    ``args_contains`` of WRITE / terminal-output expectations (i.e. NOT read
    tools) plus every ``response_contains`` / ``result_contains`` value."""
    values: set[str] = set()
    expect = expect or {}
    for item in expect.get("tool_expectations") or []:
        if not isinstance(item, dict):
            continue
        tool = str(item.get("tool") or "")
        if not tool.endswith(READ_SUFFIXES):
            _collect_strings(item.get("args_contains"), values, False)
        for key in OUTPUT_KEYS:
            if key in item:
                _collect_strings(item[key], values, False)
    for key in OUTPUT_KEYS:
        if key in expect:
            _collect_strings(expect[key], values, False)
    return values


def input_corpus(variant_input: dict) -> str:
    """Lowercase text an agent can see or read via tools: the trigger event and
    the seeded backend state."""
    variant_input = variant_input or {}
    trigger = json.dumps(variant_input.get("trigger_input") or {})
    seed = json.dumps(variant_input.get("seed") or {})
    return (trigger + seed).lower()


def derivable_values(variant_input: dict) -> set[str]:
    """Every string scalar (len >= 4) present as data in the trigger event or
    the seeded backend. Restating any of these in a brief shortcuts the
    derivation the benchmark measures, whether or not it is also a required
    output value."""
    values: set[str] = set()
    variant_input = variant_input or {}
    _collect_strings(variant_input.get("trigger_input"), values, False)
    _collect_strings(variant_input.get("seed"), values, False)
    return values


def classify(variant_input: dict) -> dict:
    """Partition the task's required values into those an agent can derive from
    the trigger/seed and those that are fixed recipe CONSTANTS."""
    corpus = input_corpus(variant_input)
    derivable: list[str] = []
    constants: list[str] = []
    for value in required_values((variant_input or {}).get("expect") or {}):
        (derivable if value.lower() in corpus else constants).append(value)
    return {"derivable": sorted(derivable), "constants": sorted(constants)}


def recipe_constants(recipe_data_dir: Path, recipe_id: str) -> list[str]:
    """Union of the constants across every variant of ``recipe_id``."""
    constants: set[str] = set()
    pattern = f"{recipe_id}/variant_*/input.json"
    for input_path in sorted(Path(recipe_data_dir).glob(pattern)):
        variant_input = json.loads(input_path.read_text())
        constants.update(classify(variant_input)["constants"])
    return sorted(constants)


def brief_tool_names(text: str) -> list[str]:
    """Registered tool names appearing in brief text (workflow leakage)."""
    lowered = text.lower()
    return sorted({token for token in _TOOL_TOKEN_RE.findall(lowered)
                   if token.startswith(TOOL_PREFIXES)})
