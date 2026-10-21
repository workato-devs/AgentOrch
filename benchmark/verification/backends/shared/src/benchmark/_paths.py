"""Resolve paths for whichever benchmark variant is currently active."""

from __future__ import annotations

from pathlib import Path

import benchmark as _benchmark_package


def _active_variant_root() -> Path:
    for package_path in _benchmark_package.__path__:
        candidate = Path(package_path).resolve().parents[1]
        if candidate.name in {"real", "simulated"}:
            return candidate
    raise RuntimeError(
        "benchmark shared code must be imported through benchmark/real/src "
        "or benchmark/simulated/src"
    )


BENCHMARK_ROOT = _active_variant_root()
WORKSPACE_ROOT = BENCHMARK_ROOT.parent.parent
