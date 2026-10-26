"""Value-agnostic planning metrics vs the committed ground-truth trajectory.
plan_struct: did the model perform the same writes (tool + target + field
keys), ignoring concrete values. Efficiency and redundancy come from raw call
counts. Reads are free-form: agents may explore differently than the recipe.
Terminal-response tools (api_platform/service/genie/pub_sub/recipe_function
returns) count as writes via the generic signature branch."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

_READ_SUFFIXES = ("get_records", "search_records", "get_entries", "get_entry",
                  "search_entries")

# Exploration vs mutation: read/list/get/search/describe/schema inspection is
# orientation work; create/update/delete/post/send/publish are business
# effects. Budgets and efficiency should not treat them identically.
_EXPLORATION_PREFIXES = ("get_", "list_", "search_", "describe_", "read_",
                         "lookup_", "fetch_", "query_", "select_")
_EXPLORATION_EXACT = {"get", "list", "search", "describe", "snapshot"}


def is_exploration(tool: str) -> bool:
    op = str(tool or "").rsplit(".", 1)[-1].lower()
    return (op in _EXPLORATION_EXACT
            or op in _READ_SUFFIXES
            or op.startswith(_EXPLORATION_PREFIXES))


def _keys(value: Any) -> tuple:
    return tuple(sorted(value.keys())) if isinstance(value, dict) else ()


def write_signature(tool: str, args: dict[str, Any]) -> tuple | None:
    args = args or {}
    if tool.rsplit(".", 1)[-1] in _READ_SUFFIXES:
        return None
    if tool.startswith("workato_db_table."):
        return (tool, str(args.get("table_id")), _keys(args.get("record")))
    if tool.startswith("lookup_table."):
        table = args.get("lookup_table_id") or args.get("table_id")
        body = args.get("parameters") if isinstance(args.get("parameters"), dict) else args.get("record")
        return (tool, str(table), _keys(body))
    return (tool, _keys(args))


def _write_sigs(calls: list[dict[str, Any]]) -> Counter:
    sigs: Counter = Counter()
    for call in calls or []:
        sig = write_signature(str(call.get("tool") or ""), call.get("args") or {})
        if sig is not None:
            sigs[sig] += 1
    return sigs


def score_one(task_id: str, gold_calls: list[dict[str, Any]],
              model_calls: list[dict[str, Any]], strict_pass: bool,
              failed_calls: int, stop_reason: str) -> dict[str, Any]:
    gold_sigs = _write_sigs(gold_calls)
    model_sigs = _write_sigs(model_calls)
    missing = list((gold_sigs - model_sigs).elements())
    extra = list((model_sigs - gold_sigs).elements())

    gold_actions = len(gold_calls)
    seen: set[tuple] = set()
    redundant = 0
    for call in model_calls:
        key = (call.get("tool"), json.dumps(call.get("args"), sort_keys=True, default=str))
        if key in seen:
            redundant += 1
        seen.add(key)

    if model_calls:
        action_efficiency = round(min(1.0, max(gold_actions, 1) / len(model_calls)), 3)
    else:
        action_efficiency = 0.0

    model_reads = sum(1 for c in model_calls if is_exploration(str(c.get("tool") or "")))
    gold_mutations = sum(1 for c in gold_calls if not is_exploration(str(c.get("tool") or "")))
    return {
        "task_id": task_id,
        "plan_struct": gold_sigs == model_sigs,
        "strict_pass": bool(strict_pass),
        "action_efficiency": action_efficiency,
        "model_actions": len(model_calls),
        "gold_actions": len(gold_calls),
        "model_reads": model_reads,
        "model_mutations": len(model_calls) - model_reads,
        "gold_mutations": gold_mutations,
        "redundant_actions": redundant,
        "missing_struct": [list(sig) for sig in missing],
        "extra_writes": [list(sig) for sig in extra],
        "failed_calls": failed_calls,
        "stop_reason": stop_reason,
    }
