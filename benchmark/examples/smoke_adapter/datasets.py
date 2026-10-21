"""Public-pilot data access with strict model/ground-truth separation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[2]
INPUT_ROOT = ROOT / "input"
GROUNDTRUTH_ROOT = ROOT / "groundtruth"
MANIFEST = INPUT_ROOT / "manifest.json"
PLANNING_MODES = frozenset({"global", "local"})
INTERACTIVE_MODES = frozenset({"react", "replan"})
MODES = PLANNING_MODES | INTERACTIVE_MODES


@dataclass(frozen=True)
class Case:
    recipe_id: str
    variant_id: str
    mode: str


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def manifest() -> dict[str, Any]:
    data = _read_json(MANIFEST)
    if data.get("schema") != "agentorch-public-input":
        raise ValueError("unsupported public benchmark manifest")
    return data


def recipe_dir(recipe_id: str) -> Path:
    path = INPUT_ROOT / "recipes" / str(recipe_id)
    if not path.is_dir():
        raise KeyError(f"unknown pilot recipe {recipe_id}")
    return path


def load_model_input(recipe_id: str, mode: str) -> dict[str, Any]:
    """Load only the model-visible task projection.

    This deliberately has no variant parameter: inputs and ground truth are
    evaluator-private and must never enter a planner prompt.
    """
    if mode not in PLANNING_MODES:
        raise ValueError(f"planning mode must be one of {sorted(PLANNING_MODES)}")
    prefix = "GLOBAL_VIEW" if mode == "global" else "LOCAL_VIEW"
    directory = recipe_dir(recipe_id)
    return {
        "recipe_id": str(recipe_id),
        "mode": mode,
        "system_prompt": (directory / f"{prefix}_system.txt").read_text(encoding="utf-8"),
        "user_prompt": (directory / f"{prefix}_user.txt").read_text(encoding="utf-8"),
    }


def load_variant(recipe_id: str, variant_id: str) -> dict[str, Any]:
    """Deprecated: runtime seeds are evaluator-private verification data."""
    raise RuntimeError("interactive evaluation uses evaluator-private seeds")


def load_interactive_input(recipe_id: str, variant_id: str,
                           mode: str) -> dict[str, Any]:
    """Load the exact public ReAct prompt for one model/simulator interaction."""
    if mode not in INTERACTIVE_MODES:
        raise ValueError(f"interactive mode must be one of {sorted(INTERACTIVE_MODES)}")
    directory = recipe_dir(recipe_id)
    return {
        "recipe_id": str(recipe_id),
        "variant_id": str(variant_id),
        "mode": mode,
        "system_prompt": (directory / "REACT_system.txt").read_text(encoding="utf-8"),
        "user_prompt": (directory / f"REACT_variant_{int(variant_id):02d}_user.txt").read_text(encoding="utf-8"),
    }


def load_ground_truth(recipe_id: str, variant_id: str) -> dict[str, Any]:
    """Evaluator-only expected trace, state, and terminal result."""
    return _read_json(
        GROUNDTRUTH_ROOT / "recipes" / str(recipe_id)
        / f"variant_{int(variant_id):02d}.json"
    )


def iter_cases(*, mode: str, recipe_id: str | None = None) -> Iterator[Case]:
    if mode not in MODES:
        raise ValueError(f"unsupported mode={mode!r}")
    found = False
    for recipe in manifest()["recipes"]:
        current_recipe_id = str(recipe["recipe_id"])
        if recipe_id is not None and current_recipe_id != str(recipe_id):
            continue
        found = True
        for variant_id in recipe["variant_ids"]:
            yield Case(current_recipe_id, str(variant_id), mode)
    if recipe_id is not None and not found:
        raise KeyError(f"unknown benchmark recipe {recipe_id}")
