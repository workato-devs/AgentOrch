from __future__ import annotations

from copy import deepcopy
from typing import Any

from .context import RecipeContext
from .config import variant_label


def variant_data(ctx: RecipeContext) -> dict[str, Any]:
    data = ctx.seed.get("variant_input")
    if not isinstance(data, dict) or not data:
        raise RuntimeError(
            "seed is missing variant_input; every run must load an explicit "
            "dataset/input_recipes/<recipe_id>/variant_##/input.json"
        )
    return data


def variant_index(ctx: RecipeContext) -> int:
    value = variant_data(ctx).get("variant")
    if isinstance(value, bool) or not (
        isinstance(value, int) or (isinstance(value, str) and value.isdigit())
    ):
        raise RuntimeError(f"variant input missing integer 'variant' field: {value!r}")
    return int(value)


def trigger_input(ctx: RecipeContext) -> dict[str, Any]:
    data = variant_data(ctx).get("trigger_input")
    if not isinstance(data, dict):
        raise RuntimeError("variant input missing required trigger_input object")
    return deepcopy(data)


def require_seed_section(ctx: RecipeContext, name: str) -> dict[str, Any]:
    seed = variant_data(ctx).get("seed")
    if isinstance(seed, dict) and isinstance(seed.get(name), dict):
        return deepcopy(seed[name])
    raise RuntimeError(f"variant input missing required seed section: {name}")


def attach_variant(seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    data = variant_data(ctx)
    seed["variant"] = variant_index(ctx)
    seed["variant_label"] = variant_label(seed["variant"])
    seed["variant_input"] = deepcopy(data)
    # Generic fault-injection / job-context propagation. When a variant input
    # declares one of these, make sure it reaches the executor seed even if a
    # recipe's own seeder does not copy it explicitly. Guarded so it never
    # overrides a seeder that already set the key, and only fires when the
    # variant input opts in -- existing variants (which omit these) are
    # unaffected. This lets error/catch branches be exercised uniformly.
    for key in ("force_action_error", "job_context"):
        if key not in seed and isinstance(data.get(key), dict):
            seed[key] = deepcopy(data[key])
    return seed
