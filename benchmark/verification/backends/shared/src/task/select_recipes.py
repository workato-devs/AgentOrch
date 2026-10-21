"""Selects the mock-only pilot set: registered recipes whose committed gold
run touched ONLY Workato-internal tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark._paths import BENCHMARK_ROOT

# Only the Workato-internal mock harness tools count as internal: a blanket
# "harness." prefix would admit live-backend seeding/snapshot calls
# (harness.google_sheets.*, harness.slack.*, ...) into the mock-only pilot.
INTERNAL_PREFIXES = ("workato_", "lookup_table.",
                     "harness.workato_db_table.", "harness.lookup_table.")


def _tools(output: dict[str, Any]) -> list[str]:
    calls = list(output.get("tool_calls") or []) + list(output.get("harness_tool_calls") or [])
    calls += list((output.get("details") or {}).get("seed_harness_tool_calls") or [])
    return [str(call.get("tool") or "") for call in calls]


def is_internal_only(output: dict[str, Any]) -> bool:
    tools = _tools(output)
    return bool(tools) and all(t.startswith(INTERNAL_PREFIXES) for t in tools)


def pilot_ids(ground_truth_root: Path) -> list[str]:
    from benchmark.recipes import RUNNERS
    ids: list[str] = []
    for recipe_id in RUNNERS:
        path = ground_truth_root / recipe_id / "variant_00" / "output.json"
        if not path.exists():
            continue
        if is_internal_only(json.loads(path.read_text())):
            ids.append(recipe_id)
    return sorted(ids, key=int)


if __name__ == "__main__":
    print(json.dumps(pilot_ids(BENCHMARK_ROOT / "output")))
