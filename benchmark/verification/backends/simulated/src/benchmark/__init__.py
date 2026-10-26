"""Simulated-connector benchmark overlay.

Shared recipes and runtime modules live in ``benchmark/shared``. Modules in
this package override that shared layer with deterministic connector behavior.
"""

from pathlib import Path

_SHARED_PACKAGE = (
    Path(__file__).resolve().parents[3] / "shared" / "src" / "benchmark"
)
if not _SHARED_PACKAGE.is_dir():
    raise ImportError(f"missing shared benchmark package: {_SHARED_PACKAGE}")
__path__.append(str(_SHARED_PACKAGE))
