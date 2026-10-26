"""Activate one vendored connector backend before importing ``benchmark``."""

from __future__ import annotations

import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
PUBLIC_ROOT = ROOT.parent
BACKENDS_ROOT = ROOT / "backends"
DATASET_ROOT = ROOT / "dataset"
OUTPUT_ROOT = PUBLIC_ROOT / "outputs/connector-runtime"
SUPPORTED_BACKENDS = frozenset({"simulated", "real"})
_ACTIVE_BACKEND: str | None = None


def activate(backend: str, *, output_dir: Path | None = None) -> Path:
    """Select a backend and return its source root.

    The real and simulated overlays both use the Python package name
    ``benchmark`` and therefore cannot coexist in one interpreter. Selection
    must happen before importing that package and is immutable for the process.
    """

    global _ACTIVE_BACKEND
    backend = str(backend).strip().lower()
    if backend not in SUPPORTED_BACKENDS:
        raise ValueError(f"backend must be one of {sorted(SUPPORTED_BACKENDS)}")
    if _ACTIVE_BACKEND is not None and _ACTIVE_BACKEND != backend:
        raise RuntimeError(
            f"connector backend already activated as {_ACTIVE_BACKEND!r}"
        )
    loaded = sys.modules.get("benchmark")
    if loaded is not None and _ACTIVE_BACKEND is None:
        raise RuntimeError("benchmark was imported before backend activation")

    source_root = BACKENDS_ROOT / backend / "src"
    shared_root = BACKENDS_ROOT / "shared" / "src" / "benchmark"
    if not (source_root / "benchmark/__init__.py").is_file():
        raise RuntimeError(f"vendored {backend} backend is missing: {source_root}")
    if not shared_root.is_dir():
        raise RuntimeError(f"vendored shared backend is missing: {shared_root}")

    source_text = str(source_root)
    if source_text not in sys.path:
        sys.path.insert(0, source_text)
    shared_source_text = str(BACKENDS_ROOT / "shared" / "src")
    if shared_source_text not in sys.path:
        sys.path.insert(1, shared_source_text)
    os.environ["BENCHMARK_DATASET_DIR"] = str(DATASET_ROOT)
    selected_output = (output_dir or OUTPUT_ROOT / backend).resolve()
    selected_output.mkdir(parents=True, exist_ok=True)
    if output_dir is not None:
        os.environ["BENCHMARK_OUTPUT_DIR"] = str(selected_output)
    else:
        os.environ.setdefault("BENCHMARK_OUTPUT_DIR", str(selected_output))
    _ACTIVE_BACKEND = backend
    return source_root


def active_backend() -> str | None:
    return _ACTIVE_BACKEND
